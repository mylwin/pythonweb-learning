from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.schemas.users import UserRegisterRequest, UserRegisterResponse
from jjtq.backend.services import users as users_service

# 创建 router 实例
router = APIRouter(prefix="/api/user", tags=["users"])


# 用户注册
@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: UserRegisterRequest,
):
    register_data = await users_service.register_user(
        db, payload.username, payload.password
    )
    if register_data is None:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "message": "用户名已存在", "data": None},
        )
    return {"code": 200, "message": "success", "data": register_data}
