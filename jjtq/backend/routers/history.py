from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.dependencies.auth import get_current_user
from jjtq.backend.models.users import User
from jjtq.backend.schemas.history import (
    HistoryAddRequest,
    HistoryAddResponse,
    HistoryDeleteResponse,
    HistoryListRequest,
    HistoryListResponse,
)
from jjtq.backend.services import history as history_service
from jjtq.backend.utils.response import success_response

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add", response_model=HistoryAddResponse)
async def add_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: HistoryAddRequest,
):
    """
    记录当前登录用户的一次新闻浏览。

    :param db: 数据库异步会话
    :param current_user: 根据有效 Bearer 令牌获取的用户
    :param payload: JSON 请求体，newsId 为大于等于 1 的新闻 ID
    :return: 包含历史记录 ID、用户 ID、新闻 ID 和浏览时间的统一成功响应
    """
    history = await history_service.add_history(db, current_user, payload.news_id)
    return success_response(message="记录浏览历史成功", data=history)


@router.get("/list", response_model=HistoryListResponse)
async def get_history_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[HistoryListRequest, Query()],
):
    """
    分页查询当前登录用户的浏览历史。

    :param db: 数据库异步会话
    :param current_user: 根据有效 Bearer 令牌获取的用户
    :param params: 查询参数 page、pageSize，默认分别为 1、50，每页最多 100 条
    :return: 包含 list、total、hasMore 的统一成功响应，列表项 id 为新闻 ID
    """
    history_list = await history_service.get_history_list(
        db, current_user, params.page, params.page_size
    )
    return success_response(data=history_list)


@router.delete("/delete/{id}", response_model=HistoryDeleteResponse)
async def remove_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    news_id: Annotated[int, Path(alias="id", ge=1, title="新闻编号")],
):
    """
    按新闻 ID 删除当前登录用户的全部对应浏览记录。

    :param db: 数据库异步会话
    :param current_user: 根据有效 Bearer 令牌获取的用户
    :param news_id: 对应路径参数 id，取历史列表项中的新闻 ID，必须大于等于 1
    :return: data 为 None 的统一成功响应，重复删除仍返回成功
    """
    await history_service.remove_history(db, current_user, news_id)
    return success_response(message="删除浏览历史成功")


@router.delete("/clear", response_model=HistoryDeleteResponse)
async def clear_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    清空当前登录用户的全部浏览历史。

    :param db: 数据库异步会话
    :param current_user: 根据有效 Bearer 令牌获取的用户
    :return: data 为 None 的统一成功响应，空历史重复清空仍返回成功
    """
    await history_service.clear_history(db, current_user)
    return success_response(message="清空浏览历史成功")
