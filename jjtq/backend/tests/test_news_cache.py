import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from jjtq.backend.config.database import Settings, get_db
from jjtq.backend.config.redis import create_redis_client
from jjtq.backend.dependencies.redis import get_redis
from jjtq.backend.main import app
from jjtq.backend.models.news import News
from jjtq.backend.utils.news_cache import news_list_key


class AsyncTestSession:
    """使用同步内存数据库验证异步接口，并统计实际数据库查询次数。"""

    def __init__(self, session):
        """保存测试会话并初始化查询计数。"""
        self.session = session
        self.query_count = 0

    async def execute(self, statement):
        """执行查询并累加计数。"""
        self.query_count += 1
        return self.session.execute(statement)


class FakeRedis:
    """模拟缓存读写、过期时间以及连接故障。"""

    def __init__(self):
        """初始化缓存内容和故障开关。"""
        self.values = {}
        self.expirations = {}
        self.fail_get = False
        self.fail_set = False

    async def get(self, key):
        """返回缓存值，模拟未命中或读取失败。"""
        if self.fail_get:
            raise RedisConnectionError('模拟 Redis 读取失败')
        return self.values.get(key)

    async def set(self, key, value, *, ex):
        """保存缓存内容和过期秒数，或模拟写入失败。"""
        if self.fail_set:
            raise RedisConnectionError('模拟 Redis 写入失败')
        self.values[key] = value
        self.expirations[key] = ex


class SharedSettingsTests(unittest.TestCase):
    """验证数据库和 Redis 可以共用同一个环境文件。"""

    def test_database_settings_ignore_redis_configuration(self):
        """数据库配置读取环境文件时忽略 Redis 配置项。"""
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / '.env'
            env_file.write_text(
                'ASYNC_DATABASE_URL=mysql+aiomysql://user:password@localhost/test\n'
                'REDIS_URL=redis://localhost:6379/1\n'
            )
            with patch.dict(os.environ, {}, clear=True):
                settings = Settings(_env_file=env_file)
            self.assertEqual(
                settings.async_database_url,
                'mysql+aiomysql://user:password@localhost/test',
            )


class NewsCacheTests(unittest.IsolatedAsyncioTestCase):
    """验证新闻列表缓存、参数隔离与故障降级。"""

    def setUp(self):
        """创建独立数据库及缓存，替换项目依赖。"""
        self.engine = create_engine('sqlite:///:memory:')
        News.__table__.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            News(id=1, title='中文标题', content='正文', category_id=1,
                 views=9, publish_time=datetime(2026, 1, 1, 12)),
            News(id=2, title='其他新闻', content='内容', category_id=2,
                 views=3, publish_time=datetime(2026, 1, 2, 12)),
        ])
        self.session.commit()
        self.db = AsyncTestSession(self.session)
        self.cache = FakeRedis()

        async def override_db():
            """模拟数据库会话依赖的提交及回滚。"""
            try:
                yield self.db
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: self.cache

    def tearDown(self):
        """恢复依赖并释放内存数据库。"""
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)
        self.session.close()
        self.engine.dispose()

    async def request(self, query=''):
        """
        通过 ASGI 请求新闻列表。

        :param query: 不含问号的查询字符串
        :return: HTTP 状态码及 JSON 响应
        """
        messages = []

        async def receive():
            """提供空请求体。"""
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        async def send(message):
            """收集响应状态与响应体。"""
            messages.append(message)

        await app({
            'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
            'method': 'GET', 'scheme': 'http', 'path': '/api/news/list',
            'raw_path': b'/api/news/list', 'query_string': query.encode(),
            'root_path': '', 'headers': [],
            'server': ('test', 80), 'client': ('test', 123),
        }, receive, send)
        return messages[0]['status'], json.loads(
            b''.join(message.get('body', b'') for message in messages[1:])
        )

    async def test_cache_miss_hit_and_response_contract(self):
        """首次回源并缓存；再次命中时响应一致且不再查询数据库。"""
        status, first = await self.request()
        self.assertEqual(status, 200)
        self.assertEqual(self.db.query_count, 1)
        self.assertEqual([item['id'] for item in first['data']['list']], [2, 1])
        self.assertEqual(first['data']['list'][1]['publish_time'], '2026-01-01T12:00:00')
        self.assertEqual(first['data']['list'][1]['content'], '正文')
        key = news_list_key(None, 1, 10)
        self.assertEqual(json.loads(self.cache.values[key]), first['data']['list'])
        self.assertTrue(600 <= self.cache.expirations[key] <= 660)
        status, second = await self.request()
        self.assertEqual(status, 200)
        self.assertEqual(first, second)
        self.assertEqual(self.db.query_count, 1)

    async def test_category_page_and_page_size_are_isolated(self):
        """不同分类、页码及每页数量的缓存各自独立。"""
        for query in ('', 'categoryId=1', 'page=2', 'pageSize=20', 'categoryId=0'):
            status, _ = await self.request(query)
            self.assertEqual(status, 200)
        self.assertEqual(self.db.query_count, 5)
        self.assertEqual(len(self.cache.values), 5)
        for query in ('', 'categoryId=1', 'page=2', 'pageSize=20', 'categoryId=0'):
            status, _ = await self.request(query)
            self.assertEqual(status, 200)
        self.assertEqual(self.db.query_count, 5)

    async def test_empty_results_are_cached_with_shorter_ttl(self):
        """空列表也是缓存命中，使用较短的随机过期时间。"""
        status, first = await self.request('categoryId=999')
        self.assertEqual(status, 200)
        self.assertEqual(first['data']['list'], [])
        key = news_list_key(999, 1, 10)
        self.assertTrue(60 <= self.cache.expirations[key] <= 70)
        status, second = await self.request('categoryId=999')
        self.assertEqual(status, 200)
        self.assertEqual(second, first)
        self.assertEqual(self.db.query_count, 1)

    async def test_corrupt_cache_is_reloaded_and_replaced(self):
        """损坏的 JSON 或错误的数据结构回源并覆盖原缓存。"""
        key = news_list_key(None, 1, 10)
        for corrupted in ('{', '{}', '[1]'):
            self.cache.values[key] = corrupted
            before = self.db.query_count
            status, body = await self.request()
            self.assertEqual(status, 200)
            self.assertEqual(self.db.query_count, before + 1)
            self.assertEqual(json.loads(self.cache.values[key]), body['data']['list'])

    async def test_redis_failures_fall_back_to_database(self):
        """缓存读取和回填失败时仍能返回数据库结果。"""
        self.cache.fail_get = True
        self.cache.fail_set = True
        status, first = await self.request('categoryId=1')
        self.assertEqual(status, 200)
        self.assertEqual([item['id'] for item in first['data']['list']], [1])
        status, second = await self.request('categoryId=1')
        self.assertEqual(status, 200)
        self.assertEqual(first, second)
        self.assertEqual(self.db.query_count, 2)

    async def test_database_errors_are_not_hidden(self):
        """数据库查询失败向外抛出，不写入错误结果。"""
        with patch.object(self.db, 'execute', side_effect=RuntimeError('数据库不可用')):
            with self.assertRaises(RuntimeError):
                await self.request()
        self.assertEqual(self.cache.values, {})

    async def test_query_validation_is_unchanged(self):
        """分页参数校验保持原有接口行为。"""
        for query in ('page=0', 'pageSize=9', 'pageSize=101', 'categoryId=abc'):
            status, _ = await self.request(query)
            self.assertEqual(status, 422, query)
        self.assertEqual(self.db.query_count, 0)
        self.assertEqual(self.cache.values, {})

    async def test_client_rejects_other_database_even_when_query_overrides_path(self):
        """检查 URL 最终解析结果，避免查询参数覆盖路径而误写数据库 0。"""
        for url in ('redis://localhost:6379/0', 'redis://localhost:6379/1?db=0'):
            with patch.dict('os.environ', {'REDIS_URL': url}):
                with self.assertRaises(ValueError):
                    create_redis_client()
        with patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379/1'}):
            client = create_redis_client()
            try:
                self.assertEqual(client.connection_pool.connection_kwargs['db'], 1)
            finally:
                await client.aclose()

    async def test_app_lifecycle_reuses_and_closes_client(self):
        """应用生命周期复用 Redis 客户端，关闭时释放两种连接池。"""
        client = AsyncMock()
        with (
            patch('jjtq.backend.main.create_redis_client', return_value=client) as factory,
            patch('jjtq.backend.main.async_engine', new_callable=AsyncMock) as engine,
        ):
            async with app.router.lifespan_context(app):
                self.assertIs(app.state.redis_client, client)
                factory.assert_called_once_with()
            client.aclose.assert_awaited_once_with()
            engine.dispose.assert_awaited_once_with()

    async def test_mysql_pool_is_disposed_when_redis_close_fails(self):
        """Redis 关闭异常时仍释放 MySQL 连接池，并继续抛出异常。"""
        client = AsyncMock()
        client.aclose.side_effect = RuntimeError('Redis 关闭失败')
        with (
            patch('jjtq.backend.main.create_redis_client', return_value=client),
            patch('jjtq.backend.main.async_engine', new_callable=AsyncMock) as engine,
        ):
            with self.assertRaises(RuntimeError):
                async with app.router.lifespan_context(app):
                    pass
            engine.dispose.assert_awaited_once_with()
