from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.models.users import User
from jjtq.backend.schemas.users import (
    UserLoginInfoResponse,
    UserLoginResponse,
    UserProfileUpdateResponse,
    UserRegisterInfoResponse,
    UserRegisterResponse,
    UserUpdateRequest,
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


async def update_user_info(
    db: AsyncSession, user: User, payload: UserUpdateRequest
) -> UserProfileUpdateResponse:
    """
    更新当前用户指定的资料。

    :param db: 数据库异步会话
    :param user: 已认证的用户对象
    :param payload: 要更新的用户资料
    :return: 更新后的用户资料
    :raises HTTPException: 手机号已被其他用户使用
    """
    # model_dump 忽略未设置字段，留下要更新的字段
    fields = payload.model_dump(exclude_unset=True)
    try:
        updated_user = await users_crud.update_user_info(db, user, fields)
    except IntegrityError as error:
        # MySQL 唯一键冲突码为 1062；SQLite 测试使用列名识别。
        original = error.orig
        is_duplicate = bool(
            original is not None and original.args and original.args[0] == 1062
        )
        is_phone_unique = (
            "unique constraint failed: user.phone" in str(original).lower()
        )
        if fields.get("phone") is not None and (is_duplicate or is_phone_unique):
            raise HTTPException(status_code=409, detail="手机号已被使用") from error
        raise
    return UserProfileUpdateResponse.model_validate(updated_user)
