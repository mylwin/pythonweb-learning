import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
from jjtq.backend.crud import favorite as favorite_crud
from jjtq.backend.main import app
from jjtq.backend.models.favorite import Favorite
from jjtq.backend.models.news import News
from jjtq.backend.models.users import User, UserToken
from jjtq.backend.utils.security import hash_token


class AsyncTestSession:
    """将同步内存数据库适配为接口测试所需的异步会话。"""

    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, instance):
        self.session.add(instance)

    async def flush(self):
        self.session.flush()

    async def refresh(self, instance):
        self.session.refresh(instance)

    @asynccontextmanager
    async def begin_nested(self):
        with self.session.begin_nested():
            yield


class FavoriteWriteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        for table in (User.__table__, UserToken.__table__, News.__table__, Favorite.__table__):
            table.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            User(id=1, username="alice", password="hash"),
            User(id=2, username="bob", password="hash"),
            News(id=10, title="新闻", content="内容", category_id=1),
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
            try:
                yield AsyncTestSession(self.session)
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

        app.dependency_overrides[get_db] = override_db

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        self.session.close()
        self.engine.dispose()

    async def request(self, method, action, query="newsId=10", token=None):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        path = f"/api/favorite/{action}"
        headers = [] if token is None else [(b"authorization", f"Bearer {token}".encode())]
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

    async def test_authentication_and_validation(self):
        for method, action in (("POST", "add"), ("DELETE", "remove")):
            for token in (None, "invalid", "d" * 32, "c" * 32):
                status, _ = await self.request(method, action, token=token)
                self.assertEqual(status, 401)
            for query in ("", "newsId=0", "newsId=-1", "newsId=abc"):
                status, _ = await self.request(method, action, query, "a" * 32)
                self.assertEqual(status, 422)

    async def test_add_remove_are_idempotent_and_user_scoped(self):
        status, first = await self.request("POST", "add", token="a" * 32)
        self.assertEqual(status, 200)
        status, second = await self.request("POST", "add", token="a" * 32)
        self.assertEqual(status, 200)
        self.assertEqual(first["data"], second["data"])
        self.assertEqual(first["data"]["userId"], 1)
        status, _ = await self.request("POST", "add", token="b" * 32)
        self.assertEqual(status, 200)
        for _ in range(2):
            status, _ = await self.request("DELETE", "remove", token="a" * 32)
            self.assertEqual(status, 200)
        favorites = self.session.scalars(select(Favorite)).all()
        self.assertEqual([(item.user_id, item.news_id) for item in favorites], [(2, 10)])

    async def test_add_missing_news(self):
        status, _ = await self.request("POST", "add", "newsId=999", "a" * 32)
        self.assertEqual(status, 404)
        self.assertEqual(self.session.scalars(select(Favorite)).all(), [])

    async def test_list_and_clear_require_authentication(self):
        for method, action in (("GET", "list"), ("DELETE", "clear")):
            for token in (None, "invalid", "d" * 32, "c" * 32):
                status, _ = await self.request(method, action, "", token)
                self.assertEqual(status, 401)

    async def test_list_validates_pagination(self):
        for query in (
            "page=0", "page=-1", "page=abc", "pageSize=0",
            "pageSize=-1", "pageSize=101", "pageSize=abc",
        ):
            status, _ = await self.request("GET", "list", query, "a" * 32)
            self.assertEqual(status, 422, query)

    async def test_list_pagination_sorting_and_user_isolation(self):
        favorite_time = datetime(2026, 1, 1, 12)
        for news_id in range(11, 23):
            self.session.add(News(
                id=news_id, title=f"新闻{news_id}", content="正文不应返回",
                category_id=1,
            ))
        self.session.add_all([
            Favorite(user_id=1, news_id=news_id, created_at=favorite_time)
            for news_id in range(10, 23)
        ])
        # 孤立收藏和其他用户收藏都不能影响当前用户的列表、总数和分页。
        self.session.add_all([
            Favorite(user_id=1, news_id=999),
            Favorite(user_id=2, news_id=10),
        ])
        self.session.commit()

        status, first = await self.request("GET", "list", "", "a" * 32)
        self.assertEqual(status, 200)
        self.assertEqual(first["data"]["total"], 13)
        self.assertTrue(first["data"]["hasMore"])
        self.assertEqual([item["id"] for item in first["data"]["list"]], list(range(22, 12, -1)))
        item = first["data"]["list"][0]
        self.assertEqual(set(item), {
            "id", "title", "description", "image", "author",
            "publishTime", "categoryId", "views", "favoriteTime",
        })
        self.assertIsNone(item["image"])
        self.assertEqual(item["favoriteTime"], favorite_time.isoformat())

        for query, expected, has_more in (
            ("page=2&pageSize=10", [12, 11, 10], False),
            ("page=20&pageSize=10", [], False),
            ("page=2&pageSize=2", [20, 19], True),
            ("pageSize=100", list(range(22, 9, -1)), False),
        ):
            status, body = await self.request("GET", "list", query, "a" * 32)
            self.assertEqual(status, 200)
            self.assertEqual(body["data"]["total"], 13)
            self.assertEqual(body["data"]["hasMore"], has_more)
            self.assertEqual([item["id"] for item in body["data"]["list"]], expected)

        status, body = await self.request("GET", "list", "", "b" * 32)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual([item["id"] for item in body["data"]["list"]], [10])

    async def test_clear_is_idempotent_and_removes_only_current_users_records(self):
        self.session.add_all([
            Favorite(user_id=1, news_id=10),
            Favorite(user_id=1, news_id=999),
            Favorite(user_id=2, news_id=10),
        ])
        self.session.commit()
        for _ in range(2):
            status, body = await self.request("DELETE", "clear", "", "a" * 32)
            self.assertEqual(status, 200)
            self.assertEqual(body, {"code": 200, "message": "清空收藏成功", "data": None})
        favorites = self.session.scalars(select(Favorite)).all()
        self.assertEqual([(item.user_id, item.news_id) for item in favorites], [(2, 10)])
        status, body = await self.request("GET", "list", "", "a" * 32)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"], {"list": [], "total": 0, "hasMore": False})

    async def test_failed_clear_rolls_back(self):
        self.session.add(Favorite(user_id=1, news_id=10))
        self.session.commit()
        clear = favorite_crud.clear

        async def failing_clear(db, user_id):
            await clear(db, user_id)
            raise RuntimeError("模拟删除后事务失败")

        with patch.object(favorite_crud, "clear", side_effect=failing_clear):
            with self.assertRaises(RuntimeError):
                await self.request("DELETE", "clear", "", "a" * 32)
        favorites = self.session.scalars(select(Favorite)).all()
        self.assertEqual([(item.user_id, item.news_id) for item in favorites], [(1, 10)])
