from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.dependencies.auth import get_current_user
from jjtq.backend.models.users import User
from jjtq.backend.schemas.users import (
    UserAuthRequest,
    UserLoginInfoResponse,
    UserUpdateRequest,
)
from jjtq.backend.services import users as users_service
from jjtq.backend.utils.response import error_response, success_response

# 创建 router 实例
router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register")
async def register_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: UserAuthRequest,
):
    """
    用户注册接口。

    :param db: 数据库异步会话
    :param payload: 注册请求体，包含用户名和密码
    :return: 统一成功响应；用户名已存在时返回 409 错误响应
    """
    register_data = await users_service.register_user(
        db, payload.username, payload.password
    )
    if register_data is None:
        return error_response(409, "用户名已存在")
    return success_response(message="注册成功", data=register_data)


@router.post("/login")
async def login_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: UserAuthRequest,
):
    """
    用户登录接口。

    :param db: 数据库异步会话
    :param payload: 登录请求体，包含用户名和密码
    :return: 统一成功响应；用户不存在或密码错误时返回 401 错误响应
    """
    login_data = await users_service.login_user(db, payload.username, payload.password)
    if login_data is None:
        return error_response(401, "用户不存在或密码错误")
    return success_response(message="登录成功", data=login_data)


@router.get("/info")
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    查询当前已登录用户的信息。

    :param current_user: 根据有效令牌获取的用户
    :return: 不包含密码的用户信息
    """
    return success_response(data=UserLoginInfoResponse.model_validate(current_user))


@router.put("/update")
async def update_current_user_info(
    payload: UserUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    更新当前登录用户的资料。

    :param payload: 要更新的资料字段
    :param db: 数据库异步会话
    :param current_user: 根据有效令牌获取的用户
    :return: 更新后的用户资料
    """
    user = await users_service.update_user_info(db, current_user, payload)
    return success_response(message="用户信息更新成功", data=user)
