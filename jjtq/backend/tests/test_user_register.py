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

    async def request(self, payload, path="/api/user/register"):
        body = json.dumps(payload).encode()
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "method": "POST", "scheme": "http",
            "path": path, "raw_path": path.encode(),
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
        self.assertEqual(body["message"], "注册成功")
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
            status, body = await self.request(payload)
            self.assertEqual(status, 422)
            self.assertEqual(body["code"], 422)
            self.assertEqual(body["message"], "请求参数校验失败")
            self.assertTrue(body["data"])
        self.assertEqual(self.count_users(), 0)

    async def test_register_then_login_with_symbol_password(self):
        payload = {"username": "用户123", "password": "secret!123"}
        status, _ = await self.request(payload)
        self.assertEqual(status, 200)
        stored_hash = self.session.scalars(select(User.password)).one()

        for _ in range(2):
            status, body = await self.request(payload, path="/api/user/login")
            self.assertEqual(status, 200)
            self.assertEqual(body["message"], "登录成功")
            self.assertEqual(body["data"]["userInfo"]["username"], "用户123")
            self.assertEqual(self.session.scalars(select(User.password)).one(), stored_hash)

    async def test_login_invalid_credentials(self):
        await self.request({"username": "alice", "password": "secret123"})
        for payload in (
            {"username": "alice", "password": "wrong123"},
            {"username": "nobody", "password": "secret123"},
        ):
            status, body = await self.request(payload, path="/api/user/login")
            self.assertEqual(status, 401)
            self.assertEqual(body, {"code": 401, "message": "用户不存在或密码错误", "data": None})

    async def test_validation_messages_do_not_echo_password(self):
        cases = (
            ({"username": "a", "password": "secret123"}, "用户名长度不能少于 2 个字符"),
            ({"username": "bad_name", "password": "secret123"}, "用户名只能包含字母或数字（支持中文）"),
            ({"username": "alice", "password": "短" * 30}, "密码长度不能超过 72 字节"),
            ({"username": "alice", "password": "12345"}, "密码长度不能少于 6 个字符"),
            ({"username": "alice"}, "请填写密码"),
        )
        for payload, message in cases:
            for path in ("/api/user/register", "/api/user/login"):
                status, body = await self.request(payload, path=path)
                self.assertEqual(status, 422)
                self.assertEqual(body["data"][0]["msg"], message)
                self.assertEqual(set(body["data"][0]), {"loc", "type", "msg"})
                if "password" in payload:
                    self.assertNotIn(payload["password"], json.dumps(body, ensure_ascii=False))

    async def test_bcrypt_compatible_existing_hash(self):
        stored_hash = bcrypt.hashpw(b"old!password", bcrypt.gensalt()).decode()
        self.session.add(User(username="olduser", password=stored_hash))
        self.session.commit()
        status, body = await self.request(
            {"username": "olduser", "password": "old!password"}, path="/api/user/login"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["userInfo"]["username"], "olduser")

    async def test_invalid_stored_hash_returns_unauthorized(self):
        self.session.add(User(username="broken", password="not-a-bcrypt-hash"))
        self.session.commit()
        status, _ = await self.request(
            {"username": "broken", "password": "secret123"}, path="/api/user/login"
        )
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
