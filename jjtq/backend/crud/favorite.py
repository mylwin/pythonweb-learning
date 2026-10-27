from sqlalchemy import exists, select
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
