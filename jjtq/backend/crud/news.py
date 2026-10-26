from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.news import Category, News


# 获取新闻分类列表
async def get_categories(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Category]:
    result = await db.execute(
        select(Category)
        # 根据排序序号和分类ID排序
        .order_by(Category.sort_order, Category.id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


# 获取新闻列表
async def get_news_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    category_id: int | None = None,
) -> list[News]:
    # 计算分页数据
    skip = (page - 1) * page_size
    statement = select(News)
    # 如果存在分类ID，则添加分类ID的筛选条件
    if category_id is not None:
        statement = statement.where(News.category_id == category_id)
    result = await db.execute(
        statement.order_by(News.publish_time.desc(), News.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    return list(result.scalars().all())


# 获取新闻详情
async def get_news_detail(db: AsyncSession, news_id: int) -> News | None:
    # 查询当前新闻详情
    news_detail = await db.execute(select(News).where(News.id == news_id))
    return news_detail.scalar_one_or_none()


# 对应新闻浏览量 +1
async def increment_views(db: AsyncSession, news_id: int) -> None:
    await db.execute(
        update(News)
        .where(News.id == news_id)
        .values(views=News.views + 1)
        .execution_options(synchronize_session=False)
    )


# 查询相关新闻
async def get_related_news(
    db: AsyncSession, news_id: int, category_id: int
) -> list[News]:
    result = await db.execute(
        select(News)
        .where(News.category_id == category_id, News.id != news_id)
        .order_by(News.publish_time.desc(), News.id.desc())
        .limit(5)
    )
    return list(result.scalars().all())
