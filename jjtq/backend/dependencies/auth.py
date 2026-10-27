import re
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.crud import users as users_crud
from jjtq.backend.models.users import User
from jjtq.backend.utils.security import hash_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    根据有效的 Bearer 令牌获取当前用户。

    :param db: 数据库异步会话
    :param credentials: Authorization 请求头中的 Bearer 凭证
    :return: 令牌对应的用户
    :raises HTTPException: 凭证缺失、无效或已过期
    """
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # 如果凭证不存在或者格式错误，则返回错误
    if credentials is None or not re.fullmatch(
        r"[0-9a-f]{32}", credentials.credentials
    ):
        raise error
    user = await users_crud.get_user_by_valid_token(
        db, hash_token(credentials.credentials)
    )
    if user is None:
        raise error
    return user
