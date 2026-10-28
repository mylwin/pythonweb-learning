from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import favorite as favorite_crud
from jjtq.backend.crud import news as news_crud
from jjtq.backend.models.users import User
from jjtq.backend.schemas.favorite import (
    FavoriteAddData,
    FavoriteCheckData,
    FavoriteListData,
    FavoriteListInfoData,
)
from jjtq.backend.utils.errors import BusinessError


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


async def add_favorite(
    db: AsyncSession,
    current_user: User,
    news_id: int,
) -> FavoriteAddData:
    """
    为当前用户添加指定新闻的收藏记录。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID
    :return: 新增或已存在的收藏记录数据
    """
    if await news_crud.get_news_detail(db, news_id) is None:
        raise BusinessError(404, "新闻不存在")
    favorite = await favorite_crud.get(db, current_user.id, news_id)
    if favorite is None:
        try:
            # 唯一约束处理并发请求，保存点避免破坏外层事务。
            async with db.begin_nested():
                favorite = await favorite_crud.add(db, current_user.id, news_id)
        except IntegrityError:
            # MySQL 可重复读下，锁定读才能看到并发事务刚提交的记录。
            favorite = await favorite_crud.get(
                db, current_user.id, news_id, for_update=True
            )
            if favorite is None:
                raise
    return FavoriteAddData(
        id=favorite.id,
        news_id=news_id,
        user_id=current_user.id,
        create_time=favorite.created_at,
    )


async def remove_favorite(
    db: AsyncSession,
    current_user: User,
    news_id: int,
) -> None:
    """
    删除当前用户对指定新闻的收藏记录。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID
    """
    await favorite_crud.remove(db, current_user.id, news_id)


async def get_favorite_list(
    db: AsyncSession,
    current_user: User,
    page: int,
    page_size: int,
) -> FavoriteListData:
    """
    获取当前用户的收藏列表。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param page: 页码，从 1 开始
    :param page_size: 每页数量
    :return: 收藏列表数据模型
    """

    favorite_list = await favorite_crud.get_list(db, current_user.id, page, page_size)
    total = await favorite_crud.get_count(db, current_user.id)
    return FavoriteListData(
        data_list=[FavoriteListInfoData.model_validate(item) for item in favorite_list],
        total=total,
        has_more=page * page_size < total,
    )


async def clear_favorites(db: AsyncSession, current_user: User) -> None:
    """清空当前用户的收藏，空列表重复清空也视为成功。"""
    await favorite_crud.clear(db, current_user.id)
