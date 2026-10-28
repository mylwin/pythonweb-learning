import json
import unittest
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
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
