from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.models.users import User
from jjtq.backend.schemas.users import (
    UserLoginData,
    UserLoginInfoData,
    UserProfileUpdateData,
    UserRegisterData,
    UserRegisterInfoData,
    UserUpdateRequest,
)
from jjtq.backend.utils.errors import BusinessError
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
) -> UserRegisterData:
    """
    注册用户并生成登录 token。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password: 待哈希的明文密码
    :return: 注册成功的认证数据
    :raises BusinessError: 用户名已存在
    """
    if await users_crud.get_user_by_username(db, username) is not None:
        raise BusinessError(409, "用户名已存在")

    password_hash = await hash_password(password)
    user = await users_crud.create_user(db, username, password_hash)

    token = await issue_token(db, user.id)
    return UserRegisterData(
        token=token,
        user_info=UserRegisterInfoData.model_validate(user),
    )


async def login_user(db: AsyncSession, username: str, password: str) -> UserLoginData:
    """
    用户登录并生成登录 token。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password: 待验证的明文密码
    :return: 登录成功的认证数据
    :raises BusinessError: 用户不存在、密码错误或登录期间密码发生变化
    """
    user = await users_crud.get_user_by_username(db, username)
    if user is None:
        raise BusinessError(401, "用户不存在或密码错误")
    verified_hash = user.password
    if not await verify_password(password, verified_hash):
        raise BusinessError(401, "用户不存在或密码错误")

    # 密码变更与签发令牌竞争时，锁定用户并确认验证过的哈希仍然有效。
    user = await users_crud.get_user_for_update(db, user.id)
    if user is None or user.password != verified_hash:
        raise BusinessError(401, "用户不存在或密码错误")

    token = await issue_token(db, user.id)
    return UserLoginData(
        token=token,
        user_info=UserLoginInfoData.model_validate(user),
    )


async def update_user_info(
    db: AsyncSession, user: User, payload: UserUpdateRequest
) -> UserProfileUpdateData:
    """
    更新当前用户指定的资料。

    :param db: 数据库异步会话
    :param user: 已认证的用户对象
    :param payload: 要更新的用户资料
    :return: 更新后的用户资料
    :raises BusinessError: 手机号已被其他用户使用
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
            raise BusinessError(409, "手机号已被使用") from error
        raise
    return UserProfileUpdateData.model_validate(updated_user)


async def update_user_password(
    db: AsyncSession,
    current_user: User,
    old_password: str,
    new_password: str,
) -> None:
    """
    更新当前用户的密码。

    :param db: 数据库异步会话
    :param current_user: 已认证的用户
    :param old_password: 用户的旧密码
    :param new_password: 用户的新密码
    :raises BusinessError: 旧密码错误、密码未变化或密码已被并发修改
    """
    if not await verify_password(old_password, current_user.password):
        raise BusinessError(400, "旧密码错误")
    if old_password == new_password:
        raise BusinessError(400, "新密码不能与旧密码相同")
    new_password_hash = await hash_password(new_password)
    updated = await users_crud.update_user_password(
        db, current_user.id, current_user.password, new_password_hash
    )
    if not updated:
        raise BusinessError(409, "密码已发生变化，请重新登录")
    # 密码更新和令牌撤销共用事务，失败时统一回滚。
    await users_crud.delete_user_tokens(db, current_user.id)
