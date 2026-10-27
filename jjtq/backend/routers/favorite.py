from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.dependencies.auth import get_current_user
from jjtq.backend.models.users import User
from jjtq.backend.schemas.favorite import FavoriteCheckResponse
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
    favorite_status = await favorite_service.get_favorite_status(db, current_user, news_id)
    return success_response(data=favorite_status)
