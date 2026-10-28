from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.dependencies.auth import get_current_user
from jjtq.backend.models.users import User
from jjtq.backend.schemas.favorite import (
    FavoriteAddResponse,
    FavoriteCheckResponse,
    FavoriteClearResponse,
    FavoriteListRequest,
    FavoriteListResponse,
    FavoriteRemoveResponse,
)
from jjtq.backend.services import favorite as favorite_service
from jjtq.backend.utils.response import success_response

# 创建 router 实例
router = APIRouter(prefix="/api/favorite", tags=["favorite"])


@router.get("/check", response_model=FavoriteCheckResponse)
async def check_favorite_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    news_id: Annotated[int, Query(alias="newsId", title="新闻编号", ge=1)],
):
    """
    查询当前用户是否收藏指定新闻。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID，对应查询参数 newsId
    :return: 包含 isFavorite 的统一成功响应
    """
    favorite_status = await favorite_service.get_favorite_status(
        db, current_user, news_id
    )
    return success_response(data=favorite_status)


@router.post("/add", response_model=FavoriteAddResponse)
async def add_favorite(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    news_id: Annotated[int, Query(alias="newsId", title="新闻编号", ge=1)],
):
    """
    添加收藏。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID，对应查询参数 newsId
    :return: 统一成功响应
    """
    favorite_data = await favorite_service.add_favorite(db, current_user, news_id)
    return success_response(message="收藏成功", data=favorite_data)


@router.delete("/remove", response_model=FavoriteRemoveResponse)
async def remove_favorite(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    news_id: Annotated[int, Query(alias="newsId", title="新闻编号", ge=1)],
):
    """
    删除收藏。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 新闻 ID，对应查询参数 newsId
    :return: 统一成功响应
    """
    await favorite_service.remove_favorite(db, current_user, news_id)
    return success_response(message="取消收藏成功")


@router.get("/list", response_model=FavoriteListResponse)
async def get_favorite_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[FavoriteListRequest, Query()],
):
    """
    分页获取当前用户的有效收藏，按收藏时间和 ID 倒序排列。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param params: 页码及每页数量，对应查询参数 page、pageSize
    :return: 包含 list、total 和 hasMore 的统一成功响应
    """
    favorite_list = await favorite_service.get_favorite_list(
        db, current_user, params.page, params.page_size
    )
    return success_response(data=favorite_list)


@router.delete("/clear", response_model=FavoriteClearResponse)
async def clear_favorites(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """清空当前登录用户的全部收藏。"""
    await favorite_service.clear_favorites(db, current_user)
    return success_response(message="清空收藏成功")
