import json
import logging
from random import randint
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from jjtq.backend.constants.cache import (
    NEWS_LIST_EMPTY_TTL_JITTER_SECONDS,
    NEWS_LIST_EMPTY_TTL_SECONDS,
    NEWS_LIST_KEY_TEMPLATE,
    NEWS_LIST_TTL_JITTER_SECONDS,
    NEWS_LIST_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


def news_list_key(category_id: int | None, page: int, page_size: int) -> str:
    """
    根据列表的全部筛选和分页参数生成缓存键。

    :param category_id: 分类 ID，None 表示全部分类
    :param page: 页码，从 1 开始
    :param page_size: 每页新闻数量
    :return: 分类、页码和每页数量隔离的缓存键
    """
    return NEWS_LIST_KEY_TEMPLATE.format(
        category_id="all" if category_id is None else category_id,
        page=page,
        page_size=page_size,
    )


async def get_news_list(cache: Redis, key: str) -> list[dict[str, Any]] | None:
    """
    从 Redis 读取已序列化的新闻列表。

    :param cache: 应用共享的异步 Redis 客户端
    :param key: 当前分类及分页对应的缓存键
    :return: 命中时返回列表，空列表也是命中；未命中或缓存不可用时返回 None
    """
    try:
        cached = await cache.get(key)
        if cached is None:
            return None
        data = json.loads(cached)
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise ValueError("新闻列表缓存格式无效")
        return data
    except (RedisError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        # Redis 不可用或缓存内容损坏时回源，后续写入会覆盖损坏的数据。
        logger.warning("读取新闻列表缓存失败，将查询数据库")
        return None


async def set_news_list(cache: Redis, key: str, data: list[dict[str, Any]]) -> None:
    """
    缓存新闻列表，并为正常与空结果设置不同的随机过期时间。

    :param cache: 应用共享的异步 Redis 客户端
    :param key: 当前分类及分页对应的缓存键
    :param data: 已转换为 JSON 兼容格式的新闻列表，可为空
    """
    ttl = (
        NEWS_LIST_TTL_SECONDS + randint(0, NEWS_LIST_TTL_JITTER_SECONDS)
        if data
        else NEWS_LIST_EMPTY_TTL_SECONDS + randint(0, NEWS_LIST_EMPTY_TTL_JITTER_SECONDS)
    )
    try:
        await cache.set(key, json.dumps(data, ensure_ascii=False), ex=ttl)
    except RedisError:
        # 缓存回填失败不影响已查询到的数据库结果。
        logger.warning("写入新闻列表缓存失败，返回数据库结果")
