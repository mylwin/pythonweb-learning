from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import news as news_crud
from jjtq.backend.schemas.news import NewsDetailData, RelatedNewsData
from jjtq.backend.utils import news_cache
from jjtq.backend.utils.errors import BusinessError


async def get_news_list(
    db: AsyncSession,
    cache: Redis,
    page: int,
    page_size: int,
    category_id: int | None,
) -> list[dict[str, Any]]:
    """
    通过旁路缓存获取新闻列表，未命中或缓存不可用时查询数据库。

    :param db: 数据库异步会话
    :param cache: 应用共享的 Redis 客户端，使用数据库 1
    :param page: 页码，从 1 开始
    :param page_size: 每页记录数
    :param category_id: 分类 ID，None 表示全部分类
    :return: 与现有接口字段一致的新闻列表，无数据时返回空列表
    """
    key = news_cache.news_list_key(category_id, page, page_size)
    cached = await news_cache.get_news_list(cache, key)
    if cached is not None:
        return cached

    rows = await news_crud.get_news_list(
        db, page=page, page_size=page_size, category_id=category_id
    )
    # 先统一转换，再返回和写缓存，确保命中与未命中响应完全一致。
    data = jsonable_encoder(rows)
    await news_cache.set_news_list(cache, key, data)
    return data


async def get_news_detail(db: AsyncSession, news_id: int) -> NewsDetailData:
    """
    获取新闻详情并累加浏览量。

    :param db: 数据库异步会话
    :param news_id: 新闻 ID
    :return: 新闻详情
    :raises BusinessError: 新闻不存在
    """
    # 查询新闻
    news_detail = await news_crud.get_news_detail(db, news_id)
    if news_detail is None:
        raise BusinessError(404, "新闻不存在")

    # 浏览量 +1
    await news_crud.increment_views(db, news_id)

    # 更新 ORM 对象中的浏览量
    await db.refresh(news_detail, attribute_names=["views"])

    # 查询相关新闻
    related_news = await news_crud.get_related_news(
        db, news_id, news_detail.category_id
    )

    # 构造响应，事务由 get_db 统一提交，异常时统一回滚
    detail = NewsDetailData.model_validate(news_detail)
    detail.related_news = [
        RelatedNewsData.model_validate(item) for item in related_news
    ]
    return detail
