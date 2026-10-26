from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud.news_crud import get_detail, get_related_news, increment_views
from jjtq.backend.schemas.news import NewsDetailData, RelatedNewsResponse


async def get_news_detail(db: AsyncSession, news_id: int) -> NewsDetailData | None:
    # 查询新闻
    news_detail = await get_detail(db, news_id)
    if news_detail is None:
        return None

    # 浏览量 +1
    await increment_views(db, news_id)

    # 更新 ORM 对象中的浏览量
    await db.refresh(news_detail, attribute_names=["views"])

    # 查询相关新闻
    related_news = await get_related_news(db, news_id, news_detail.category_id)

    # 构造响应，事务由 get_db 统一提交，异常时统一回滚
    detail = NewsDetailData.model_validate(news_detail)
    detail.related_news = [
        RelatedNewsResponse.model_validate(item) for item in related_news
    ]
    return detail
