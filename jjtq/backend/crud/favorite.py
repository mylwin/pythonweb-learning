from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.favorite import Favorite


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
