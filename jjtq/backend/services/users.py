import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.schemas.users import (
    UserLoginInfoResponse,
    UserLoginResponse,
    UserRegisterInfoResponse,
    UserRegisterResponse,
)
from jjtq.backend.utils.security import hash_password, verify_password


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

    # 生成随机 token
    token: str = uuid.uuid4().hex
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

    # 生成随机 token
    token: str = uuid.uuid4().hex
    return UserLoginResponse(
        token=token,
        user_info=UserLoginInfoResponse.model_validate(user),
    )
