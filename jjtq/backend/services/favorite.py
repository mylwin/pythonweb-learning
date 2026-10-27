from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import favorite as favorite_crud
from jjtq.backend.models.users import User
from jjtq.backend.schemas.favorite import FavoriteCheckData


async def get_favorite_status(
    db: AsyncSession,
    current_user: User,
    news_id: int,
) -> FavoriteCheckData:
    """
    查询当前用户对指定新闻的收藏状态。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID
    :return: 包含收藏状态的数据模型
    """
    is_favorite = await favorite_crud.favorite_exists(db, current_user.id, news_id)
    return FavoriteCheckData(is_favorite=is_favorite)
