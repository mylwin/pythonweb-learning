from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.schemas.users import (
    UserLoginInfoResponse,
    UserLoginResponse,
    UserRegisterInfoResponse,
    UserRegisterResponse,
)
from jjtq.backend.utils.security import (
    create_token,
    hash_password,
    hash_token,
    verify_password,
)

TOKEN_LIFETIME = timedelta(days=7)


async def issue_token(db: AsyncSession, user_id: int) -> str:
    """
    生成令牌并将摘要与用户和过期时间一起保存。

    :param db: 数据库异步会话
    :param user_id: 登录用户 ID
    :return: 返回给客户端的原始令牌
    """
    token = create_token()
    await users_crud.create_user_token(db, user_id, hash_token(token), TOKEN_LIFETIME)
    return token


async def register_user(
    db: AsyncSession, username: str, password: str
) -> UserRegisterResponse | None:
    """
    注册用户并生成登录 token。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password: 待哈希的明文密码
    :return: 认证数据；用户名已存在时返回 None
    """
    if await users_crud.get_user_by_username(db, username) is not None:
        return None

    password_hash = await hash_password(password)
    user = await users_crud.create_user(db, username, password_hash)

    token = await issue_token(db, user.id)
    return UserRegisterResponse(
        token=token,
        user_info=UserRegisterInfoResponse.model_validate(user),
    )


async def login_user(
    db: AsyncSession, username: str, password: str
) -> UserLoginResponse | None:
    """
    用户登录并生成登录 token。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password: 待验证的明文密码
    :return: 认证数据；用户不存在或密码错误时返回 None
    """
    user = await users_crud.get_user_by_username(db, username)
    if user is None or not await verify_password(password, user.password):
        return None

    token = await issue_token(db, user.id)
    return UserLoginResponse(
        token=token,
        user_info=UserLoginInfoResponse.model_validate(user),
    )
