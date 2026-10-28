from sqlalchemy import delete, exists, func, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.favorite import Favorite
from jjtq.backend.models.news import News


async def favorite_exists(
    db: AsyncSession,
    user_id: int,
    news_id: int,
) -> bool:
    """
    查询用户是否收藏指定新闻。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :param news_id: 新闻 ID
    :return: 存在收藏记录时为 True
    """
    result = await db.execute(
        select(exists().where(Favorite.user_id == user_id, Favorite.news_id == news_id))
    )
    return bool(result.scalar_one())


async def add(
    db: AsyncSession,
    user_id: int,
    news_id: int,
) -> Favorite:
    """
    添加收藏记录。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :param news_id: 新闻 ID
    :return: 新增的收藏记录对象
    """
    favorite = Favorite(user_id=user_id, news_id=news_id)
    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)
    return favorite


async def remove(
    db: AsyncSession,
    user_id: int,
    news_id: int,
) -> None:
    """
    删除收藏记录。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :param news_id: 新闻 ID
    """
    await db.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    )


async def get(
    db: AsyncSession, user_id: int, news_id: int, *, for_update: bool = False
) -> Favorite | None:
    """
    获取收藏记录；需要读取最新提交的记录时加行锁。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :param news_id: 新闻 ID
    :param for_update: 是否加行锁
    :return: 收藏记录对象；不存在时返回 None

    """
    statement = select(Favorite).where(
        Favorite.user_id == user_id, Favorite.news_id == news_id
    )
    if for_update:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_list(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> list[RowMapping]:
    """
    获取用户收藏列表。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :param page: 页码，从 1 开始
    :param page_size: 每页数量
    :return: 当前页仍存在的新闻摘要及收藏时间
    """
    skip = (page - 1) * page_size
    statement = (
        select(
            News.id, News.title, News.description, News.image, News.author,
            News.publish_time, News.category_id, News.views,
            Favorite.created_at.label("favorite_time"),
        )
        .join(Favorite, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(statement)
    return list(result.mappings().all())


async def get_count(db: AsyncSession, user_id: int) -> int:
    """
    获取用户仍有效的收藏数量，与列表使用相同筛选条件。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :return: 收藏数量
    """
    statement = (
        select(func.count())
        .select_from(Favorite)
        .join(News, News.id == Favorite.news_id)
        .where(Favorite.user_id == user_id)
    )
    result = await db.execute(statement)
    return result.scalar_one()


async def clear(db: AsyncSession, user_id: int) -> None:
    """删除当前用户的全部收藏，包括新闻已删除的残留记录。"""
    await db.execute(delete(Favorite).where(Favorite.user_id == user_id))
