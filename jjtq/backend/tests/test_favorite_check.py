import json
import unittest
from datetime import timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
from jjtq.backend.main import app
from jjtq.backend.models.favorite import Favorite
from jjtq.backend.models.users import User, UserToken
from jjtq.backend.utils.security import hash_token


class AsyncTestSession:
    """用内存数据库执行收藏查询。"""

    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)


class FavoriteCheckTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        User.__table__.create(self.engine)
        UserToken.__table__.create(self.engine)
        Favorite.__table__.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            User(id=1, username="alice", password="hash"),
            User(id=2, username="bob", password="hash"),
            Favorite(user_id=1, news_id=10),
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

    async def request(self, query, token=None):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        headers = [] if token is None else [(b"authorization", f"Bearer {token}".encode())]
        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": "/api/favorite/check",
            "raw_path": b"/api/favorite/check", "query_string": query.encode(),
            "root_path": "", "headers": headers,
            "server": ("test", 80), "client": ("test", 123),
        }, receive, send)
        return messages[0]["status"], json.loads(
            b"".join(message.get("body", b"") for message in messages[1:])
        )

    async def test_status_is_scoped_to_authenticated_user(self):
        for token, news_id, expected in (
            ("a" * 32, 10, True), ("a" * 32, 11, False),
            ("b" * 32, 10, False), ("a" * 32, 999, False),
        ):
            status, body = await self.request(f"newsId={news_id}", token)
            self.assertEqual(status, 200)
            self.assertEqual(body, {"code": 200, "message": "success", "data": {"isFavorite": expected}})

    async def test_authentication_and_parameter_validation(self):
        for token in (None, "d" * 32, "c" * 32):
            status, _ = await self.request("newsId=10", token)
            self.assertEqual(status, 401)
        for query in ("", "newsId=0", "newsId=-1", "newsId=abc"):
            status, _ = await self.request(query, "a" * 32)
            self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main()
