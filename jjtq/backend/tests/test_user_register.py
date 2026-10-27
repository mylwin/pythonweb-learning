import json
import unittest

import bcrypt
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
from jjtq.backend.main import app
from jjtq.backend.models.users import User


class AsyncTestSession:
    """用内存数据库执行真实 SQL，不依赖外部 MySQL 服务。"""

    def __init__(self, session):
        self.session = session

    def add(self, instance):
        self.session.add(instance)

    async def flush(self):
        self.session.flush()

    async def execute(self, statement):
        return self.session.execute(statement)


class UserRegisterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        User.__table__.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)

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

    async def request(self, payload):
        body = json.dumps(payload).encode()
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "method": "POST", "scheme": "http",
            "path": "/api/user/register", "raw_path": b"/api/user/register",
            "query_string": b"", "root_path": "",
            "headers": [(b"content-type", b"application/json")],
            "server": ("test", 80), "client": ("test", 123),
        }, receive, send)
        response_body = b"".join(m["body"] for m in messages[1:])
        return messages[0]["status"], json.loads(response_body)

    def count_users(self):
        return self.session.scalar(select(func.count()).select_from(User))

    async def test_register_success(self):
        status, body = await self.request({"username": "alice", "password": "secret123"})

        self.assertEqual(status, 200)
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        data = body["data"]
        self.assertEqual(set(data), {"token", "userInfo"})
        self.assertEqual(len(data["token"]), 32)
        self.assertEqual(data["userInfo"], {
            "id": 1,
            "username": "alice",
            "bio": "这个人很懒，什么都没留下",
            "avatar": None,
        })

        user = self.session.scalars(select(User)).one()
        self.assertNotEqual(user.password, "secret123")
        self.assertTrue(bcrypt.checkpw(b"secret123", user.password.encode()))

    async def test_duplicate_username(self):
        await self.request({"username": "alice", "password": "secret123"})
        status, body = await self.request({"username": "alice", "password": "another123"})

        self.assertEqual(status, 409)
        self.assertEqual(body, {"code": 409, "message": "用户名已存在", "data": None})
        self.assertEqual(self.count_users(), 1)

    async def test_invalid_payload(self):
        for payload in (
            {"username": "a", "password": "secret123"},
            {"username": "alice", "password": "12345"},
            {"username": "alice", "password": "密" * 30},
            {"username": "alice"},
        ):
            status, _ = await self.request(payload)
            self.assertEqual(status, 422)
        self.assertEqual(self.count_users(), 0)


if __name__ == "__main__":
    unittest.main()
