from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import news as news_crud
from jjtq.backend.schemas.news import NewsDetailData, RelatedNewsResponse


async def get_news_detail(db: AsyncSession, news_id: int) -> NewsDetailData | None:
    """
    获取新闻详情并累加浏览量。

    :param db: 数据库异步会话
    :param news_id: 新闻 ID
    :return: 新闻详情，不存在时返回 None
    """
    # 查询新闻
    news_detail = await news_crud.get_news_detail(db, news_id)
    if news_detail is None:
        return None

    # 浏览量 +1
    await news_crud.increment_views(db, news_id)

    # 更新 ORM 对象中的浏览量
    await db.refresh(news_detail, attribute_names=["views"])

    # 查询相关新闻
    related_news = await news_crud.get_related_news(db, news_id, news_detail.category_id)

    # 构造响应，事务由 get_db 统一提交，异常时统一回滚
    detail = NewsDetailData.model_validate(news_detail)
    detail.related_news = [
        RelatedNewsResponse.model_validate(item) for item in related_news
    ]
    return detail
