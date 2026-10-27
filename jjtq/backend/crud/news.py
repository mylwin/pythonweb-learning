from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.news import Category, News


async def get_categories(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Category]:
    """
    获取新闻分类列表。

    :param db: 数据库异步会话
    :param skip: 跳过的记录数
    :param limit: 返回的记录数上限
    :return: 新闻分类列表
    """
    result = await db.execute(
        select(Category)
        # 根据排序序号和分类ID排序
        .order_by(Category.sort_order, Category.id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_news_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    category_id: int | None = None,
) -> list[News]:
    """
    获取新闻列表。

    :param db: 数据库异步会话
    :param page: 页码，从 1 开始
    :param page_size: 每页记录数
    :param category_id: 分类 ID，为空时查询全部分类
    :return: 当前页新闻列表
    """
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


async def get_news_detail(db: AsyncSession, news_id: int) -> News | None:
    """
    获取新闻详情。

    :param db: 数据库异步会话
    :param news_id: 新闻 ID
    :return: 新闻对象，不存在时返回 None
    """
    # 查询当前新闻详情
    news_detail = await db.execute(select(News).where(News.id == news_id))
    return news_detail.scalar_one_or_none()


async def increment_views(db: AsyncSession, news_id: int) -> None:
    """
    将指定新闻的浏览量原子加 1。

    :param db: 数据库异步会话
    :param news_id: 新闻 ID
    """
    await db.execute(
        update(News)
        .where(News.id == news_id)
        .values(views=News.views + 1)
        .execution_options(synchronize_session=False)
    )


async def get_related_news(
    db: AsyncSession, news_id: int, category_id: int
) -> list[News]:
    """
    查询同分类下的相关新闻。

    :param db: 数据库异步会话
    :param news_id: 当前新闻 ID，结果中会排除该新闻
    :param category_id: 分类 ID
    :return: 最多 5 条相关新闻
    """
    result = await db.execute(
        select(News)
        .where(News.category_id == category_id, News.id != news_id)
        .order_by(News.publish_time.desc(), News.id.desc())
        .limit(5)
    )
    return list(result.scalars().all())
