import json
import unittest
from datetime import timedelta
from unittest.mock import patch

import bcrypt
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jjtq.backend.config.database import get_db
from jjtq.backend.main import app
from jjtq.backend.models.users import User, UserToken
from jjtq.backend.utils.security import hash_token


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
        UserToken.__table__.create(self.engine)
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

    async def request(self, payload=None, path="/api/user/register", method="POST", token=None):
        body = json.dumps(payload).encode()
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        headers = [(b"content-type", b"application/json")]
        if token is not None:
            headers.append((b"authorization", token.encode()))
        await app({
            "type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "method": method, "scheme": "http",
            "path": path, "raw_path": path.encode(),
            "query_string": b"", "root_path": "",
            "headers": headers,
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
        token_row = self.session.scalars(select(UserToken)).one()
        self.assertEqual(token_row.user_id, user.id)
        self.assertEqual(token_row.token, hash_token(data["token"]))
        self.assertNotEqual(token_row.token, data["token"])
        database_time = self.session.scalar(select(func.now()))
        self.assertGreater(token_row.expires_at, database_time + timedelta(days=6))

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

    async def test_register_and_login_tokens_identify_user(self):
        payload = {"username": "alice", "password": "secret123"}
        status, registered = await self.request(payload)
        self.assertEqual(status, 200)
        status, logged_in = await self.request(payload, path="/api/user/login")
        self.assertEqual(status, 200)
        tokens = [registered["data"]["token"], logged_in["data"]["token"]]
        self.assertNotEqual(tokens[0], tokens[1])
        for token in tokens:
            status, body = await self.request(
                path="/api/user/info", method="GET", token=f"Bearer {token}"
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["data"]["username"], "alice")
            self.assertNotIn("password", body["data"])

    async def test_missing_invalid_and_expired_tokens_are_rejected(self):
        _, body = await self.request({"username": "alice", "password": "secret123"})
        token = body["data"]["token"]
        record = self.session.scalars(select(UserToken)).one()
        record.expires_at = self.session.scalar(select(func.now())) - timedelta(seconds=1)
        self.session.commit()
        for header in (None, "Basic abc", "Bearer invalid", "Bearer " + "0" * 32,
                       "Bearer " + token.upper(), "Bearer " + token):
            status, body = await self.request(
                path="/api/user/info", method="GET", token=header
            )
            self.assertEqual(status, 401)
            self.assertEqual(body["message"], "登录状态无效或已过期，请重新登录")

    async def test_token_without_existing_user_is_rejected(self):
        token = "a" * 32
        self.session.add(UserToken(
            user_id=999, token=hash_token(token),
            expires_at=self.session.scalar(select(func.now())) + timedelta(days=1),
        ))
        self.session.commit()
        status, _ = await self.request(
            path="/api/user/info", method="GET", token=f"Bearer {token}"
        )
        self.assertEqual(status, 401)

    async def test_token_write_failure_rolls_back_registration(self):
        with patch(
            "jjtq.backend.services.users.users_crud.create_user_token",
            side_effect=RuntimeError("令牌写入失败"),
        ):
            with self.assertRaises(RuntimeError):
                await self.request({"username": "alice", "password": "secret123"})
        self.assertEqual(self.count_users(), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(UserToken)), 0)


if __name__ == "__main__":
    unittest.main()
