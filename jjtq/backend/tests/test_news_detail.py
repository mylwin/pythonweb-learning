import json
import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from jjtq.backend.config.db_config import get_db
from jjtq.backend.main import app
from jjtq.backend.models.news_model import News


class AsyncTestSession:
    """用内存数据库执行真实 SQL，不依赖外部 MySQL 服务。"""

    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def refresh(self, instance, attribute_names):
        self.session.refresh(instance, attribute_names=attribute_names)


class NewsDetailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        News.__table__.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        for news_id in range(1, 9):
            self.session.add(News(
                id=news_id, title=f"新闻{news_id}", content="第一段\n第二段",
                image=None, author=None, category_id=2 if news_id == 8 else 1,
                views=0, publish_time=datetime(2026, 1, news_id),
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

    async def request(self, query):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "method": "GET", "scheme": "http",
            "path": "/api/news/detail", "raw_path": b"/api/news/detail",
            "query_string": query.encode(), "root_path": "", "headers": [],
            "server": ("test", 80), "client": ("test", 123),
        }, receive, send)
        body = b"".join(message.get("body", b"") for message in messages[1:])
        return messages[0]["status"], json.loads(body)

    async def test_detail_fields_views_and_related_news(self):
        for expected_views in (1, 2):
            status, body = await self.request("id=1")
            self.assertEqual(status, 200)
            self.assertEqual(body["code"], 200)
            self.assertEqual(body["message"], "success")
            data = body["data"]
            self.assertEqual(set(data), {
                "id", "title", "content", "image", "author",
                "publishTime", "categoryId", "views", "relatedNews",
            })
            self.assertEqual(data["publishTime"], "2026-01-01T00:00:00")
            self.assertIsNone(data["image"])
            self.assertIsNone(data["author"])
            self.assertEqual(data["views"], expected_views)
            self.assertEqual([row["id"] for row in data["relatedNews"]], [7, 6, 5, 4, 3])
            self.assertEqual(self.session.get(News, 1).views, expected_views)
            self.assertEqual(self.session.get(News, 7).views, 0)

    async def test_no_related_news(self):
        status, body = await self.request("id=8")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["relatedNews"], [])

    async def test_missing_and_invalid_id(self):
        status, body = await self.request("id=999")
        self.assertEqual(status, 404)
        self.assertEqual(body, {"code": 404, "message": "新闻不存在", "data": None})
        for query in ("", "id=0", "id=-1", "id=abc"):
            status, _ = await self.request(query)
            self.assertEqual(status, 422)
        self.assertEqual(self.session.get(News, 1).views, 0)

    async def test_failed_query_rolls_back_views(self):
        with patch(
            "jjtq.backend.services.news_service.get_related_news",
            side_effect=RuntimeError("查询失败"),
        ):
            with self.assertRaises(RuntimeError):
                await self.request("id=1")
        self.assertEqual(self.session.get(News, 1).views, 0)


if __name__ == "__main__":
    unittest.main()
