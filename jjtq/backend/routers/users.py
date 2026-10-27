from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.schemas.users import UserRegisterRequest
from jjtq.backend.services import users as users_service
from jjtq.backend.utils.response import error_response, success_response

# 创建 router 实例
router = APIRouter(prefix="/api/user", tags=["users"])


# 用户注册
@router.post("/register")
async def register_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: UserRegisterRequest,
):
    register_data = await users_service.register_user(
        db, payload.username, payload.password
    )
    if register_data is None:
        return error_response(409, "用户名已存在")
    return success_response(message="注册成功", data=register_data)
