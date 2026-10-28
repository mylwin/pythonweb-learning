import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
from jjtq.backend.crud import history as history_crud
from jjtq.backend.main import app
from jjtq.backend.models.history import History
from jjtq.backend.models.news import News
from jjtq.backend.models.users import User, UserToken
from jjtq.backend.utils.security import hash_token


class AsyncTestSession:
    """用同步内存数据库执行历史接口的异步数据库调用。"""

    def __init__(self, session):
        """保存测试使用的同步数据库会话。"""
        self.session = session

    async def execute(self, statement):
        """执行 SQL 语句并返回查询或写入结果。"""
        return self.session.execute(statement)

    def add(self, instance):
        """将模型对象加入当前测试事务。"""
        self.session.add(instance)

    async def flush(self):
        """刷新待写入数据，保留外层事务的回滚能力。"""
        self.session.flush()

    async def refresh(self, instance):
        """重新读取模型对象，获取数据库生成的字段。"""
        self.session.refresh(instance)


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    """验证浏览历史接口契约、去重分页、用户隔离及事务回滚。"""

    def setUp(self):
        """创建独立内存数据库，并覆盖会话依赖以验证接口事务。"""
        self.engine = create_engine("sqlite:///:memory:")
        for table in (User.__table__, UserToken.__table__, News.__table__, History.__table__):
            table.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            User(id=1, username="alice", password="hash"),
            User(id=2, username="bob", password="hash"),
            News(id=10, title="新闻", content="正文", category_id=1, views=7),
            News(id=11, title="另一条新闻", content="正文", category_id=1),
        ])
        now = self.session.scalar(select(func.now()))
        for user_id, token, lifetime in (
            (1, "a" * 32, timedelta(days=1)),
            (2, "b" * 32, timedelta(days=1)),
            (1, "c" * 32, -timedelta(seconds=1)),
        ):
            self.session.add(UserToken(
                user_id=user_id, token=hash_token(token), expires_at=now + lifetime,
            ))
        self.session.commit()

        async def override_db():
            """模拟生产会话依赖的统一提交和异常回滚。"""
            try:
                yield AsyncTestSession(self.session)
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

        app.dependency_overrides[get_db] = override_db

    def tearDown(self):
        """还原依赖覆盖并释放测试数据库。"""
        app.dependency_overrides.pop(get_db, None)
        self.session.close()
        self.engine.dispose()

    async def request(self, method, action, query="", token="a" * 32, payload=None):
        """
        通过 ASGI 调用浏览历史接口。

        :param method: HTTP 请求方法
        :param action: 相对于 /api/history/ 的接口路径
        :param query: 不包含问号的查询字符串
        :param token: Bearer 令牌，默认使用有效用户令牌，None 表示不携带凭证
        :param payload: JSON 请求体，None 表示空请求体
        :return: HTTP 状态码和解析后的 JSON 响应；未处理异常继续向外抛出
        """
        messages = []
        body = b"" if payload is None else json.dumps(payload).encode()
        headers = [(b"content-type", b"application/json")]
        if token is not None:
            headers.append((b"authorization", f"Bearer {token}".encode()))

        async def receive():
            """向 ASGI 应用提供本次请求体。"""
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            """收集 ASGI 响应消息以检查状态码和响应体。"""
            messages.append(message)

        path = f"/api/history/{action}"
        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": query.encode(),
            "root_path": "", "headers": headers,
            "server": ("test", 80), "client": ("test", 123),
        }, receive, send)
        return messages[0]["status"], json.loads(
            b"".join(message.get("body", b"") for message in messages[1:])
        )

    async def test_all_endpoints_require_valid_login(self):
        """所有历史接口拒绝缺失、格式错误、无效或过期的令牌。"""
        for method, action in (
            ("POST", "add"), ("GET", "list"),
            ("DELETE", "delete/10"), ("DELETE", "clear"),
        ):
            for token in (None, "invalid", "d" * 32, "c" * 32):
                status, body = await self.request(
                    method, action, token=token, payload={"newsId": 10} if method == "POST" else None,
                )
                self.assertEqual(status, 401, action)
                self.assertEqual(body["code"], 401)
        self.assertEqual(self.session.scalars(select(History)).all(), [])

    async def test_add_and_repeat_visit_use_current_user_and_server_time(self):
        """重复浏览分别记录事件，列表归并且不重复累加新闻浏览量。"""
        for _ in range(2):
            status, body = await self.request("POST", "add", payload={"newsId": 10})
            self.assertEqual(status, 200)
            self.assertEqual(set(body["data"]), {"id", "userId", "newsId", "viewTime"})
            self.assertEqual(body["data"]["userId"], 1)
            self.assertEqual(body["data"]["newsId"], 10)
            self.assertIsNotNone(datetime.fromisoformat(body["data"]["viewTime"]))
        self.assertEqual(len(self.session.scalars(select(History)).all()), 2)
        status, body = await self.request("GET", "list")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual([item["id"] for item in body["data"]["list"]], [10])
        # 浏览量已由新闻详情接口维护，历史接口不重复累加。
        self.assertEqual(self.session.get(News, 10).views, 7)

    async def test_add_rejects_missing_news_and_invalid_or_forged_payload(self):
        """拒绝不存在的新闻、非法编号和客户端伪造的身份或时间。"""
        status, _ = await self.request("POST", "add", payload={"newsId": 999})
        self.assertEqual(status, 404)
        for payload in (
            None, {}, {"newsId": 0}, {"newsId": -1}, {"newsId": "abc"},
            {"newsId": 10, "userId": 2}, {"newsId": 10, "viewTime": "2020-01-01"},
        ):
            status, _ = await self.request("POST", "add", payload=payload)
            self.assertEqual(status, 422, payload)
        self.assertEqual(self.session.scalars(select(History)).all(), [])

    async def test_list_uses_latest_visit_and_filters_orphans_and_other_users(self):
        """列表按最近浏览时间稳定分页，过滤孤立记录及其他用户历史。"""
        old = datetime(2026, 1, 1)
        recent = old + timedelta(days=1)
        self.session.add_all([
            History(user_id=1, news_id=10, view_time=old),
            History(user_id=1, news_id=11, view_time=recent),
            History(user_id=1, news_id=10, view_time=recent),
            History(user_id=1, news_id=999, view_time=recent),
            History(user_id=2, news_id=11, view_time=recent + timedelta(days=1)),
        ])
        self.session.commit()
        status, body = await self.request("GET", "list", "pageSize=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["total"], 2)
        self.assertTrue(body["data"]["hasMore"])
        item = body["data"]["list"][0]
        self.assertEqual(item["id"], 10)
        self.assertEqual(item["viewTime"], recent.isoformat())
        self.assertEqual(set(item), {
            "id", "title", "description", "image", "author",
            "publishTime", "categoryId", "views", "viewTime",
        })
        self.assertIsNone(item["image"])
        for query, expected in (("page=2&pageSize=1", [11]), ("page=3&pageSize=1", [])):
            status, body = await self.request("GET", "list", query)
            self.assertEqual(status, 200)
            self.assertEqual(body["data"]["total"], 2)
            self.assertFalse(body["data"]["hasMore"])
            self.assertEqual([item["id"] for item in body["data"]["list"]], expected)
        status, body = await self.request("GET", "list", token="b" * 32)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual([item["id"] for item in body["data"]["list"]], [11])

    async def test_list_defaults_to_fifty_and_caps_page_size(self):
        """默认每页返回 50 条，并支持在允许范围内调整每页数量。"""
        when = datetime(2026, 1, 1)
        for news_id in range(12, 63):
            self.session.add(News(id=news_id, title="标题", content="正文", category_id=1))
            self.session.add(History(user_id=1, news_id=news_id, view_time=when))
        self.session.commit()
        for query, length, has_more in (("", 50, True), ("pageSize=100", 51, False)):
            status, body = await self.request("GET", "list", query)
            self.assertEqual(status, 200)
            self.assertEqual(len(body["data"]["list"]), length)
            self.assertEqual(body["data"]["hasMore"], has_more)
            self.assertEqual(body["data"]["total"], 51)

    async def test_invalid_pagination_and_delete_id(self):
        """非法分页参数和删除路径中的非法新闻 ID 返回 422。"""
        for query in (
            "page=0", "page=-1", "page=abc", "pageSize=0",
            "pageSize=-1", "pageSize=101", "pageSize=abc",
        ):
            status, _ = await self.request("GET", "list", query)
            self.assertEqual(status, 422, query)
        for news_id in ("0", "-1", "abc"):
            status, _ = await self.request("DELETE", f"delete/{news_id}")
            self.assertEqual(status, 422, news_id)

    async def test_delete_uses_news_id_and_is_idempotent_and_user_scoped(self):
        """按新闻 ID 删除本人的全部重复记录，重复操作不影响其他数据。"""
        self.session.add_all([
            History(user_id=1, news_id=10), History(user_id=1, news_id=10),
            History(user_id=1, news_id=11), History(user_id=2, news_id=10),
        ])
        self.session.commit()
        for _ in range(2):
            status, body = await self.request("DELETE", "delete/10")
            self.assertEqual(status, 200)
            self.assertIsNone(body["data"])
        records = self.session.scalars(select(History).order_by(History.id)).all()
        self.assertEqual([(item.user_id, item.news_id) for item in records], [(1, 11), (2, 10)])

    async def test_clear_removes_orphans_and_is_idempotent_and_user_scoped(self):
        """清空包含孤立记录且仅作用于本人，重复清空返回空列表。"""
        self.session.add_all([
            History(user_id=1, news_id=10), History(user_id=1, news_id=999),
            History(user_id=2, news_id=10),
        ])
        self.session.commit()
        for _ in range(2):
            status, body = await self.request("DELETE", "clear")
            self.assertEqual(status, 200)
            self.assertIsNone(body["data"])
        records = self.session.scalars(select(History)).all()
        self.assertEqual([(item.user_id, item.news_id) for item in records], [(2, 10)])
        status, body = await self.request("GET", "list")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"], {"list": [], "total": 0, "hasMore": False})

    async def test_write_failures_roll_back(self):
        """添加、删除和清空操作中途失败时均回滚整个事务。"""
        self.session.add(History(user_id=1, news_id=10))
        self.session.commit()
        for method, action, name, payload in (
            ("POST", "add", "add", {"newsId": 11}),
            ("DELETE", "delete/10", "remove", None),
            ("DELETE", "clear", "clear", None),
        ):
            original = getattr(history_crud, name)

            async def failing_write(*args):
                """在真实写入后注入异常，验证外层事务的回滚行为。"""
                await original(*args)
                raise RuntimeError("模拟写入后事务失败")

            with patch.object(history_crud, name, side_effect=failing_write):
                with self.assertRaises(RuntimeError):
                    await self.request(method, action, payload=payload)
            records = self.session.scalars(select(History)).all()
            self.assertEqual([(item.user_id, item.news_id) for item in records], [(1, 10)])
