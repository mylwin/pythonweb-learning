from datetime import timedelta
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.users import User, UserToken


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    根据用户名查询用户。

    :param db: 数据库异步会话
    :param username: 用户名
    :return: 用户对象，不存在时返回 None
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_for_update(db: AsyncSession, user_id: int) -> User | None:
    """
    锁定并重新读取用户，以便校验密码状态后签发令牌。

    :param db: 数据库异步会话
    :param user_id: 用户 ID
    :return: 最新的用户对象；不存在时返回 None
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password_hash: str) -> User:
    """
    创建用户并加入当前事务。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password_hash: bcrypt 哈希后的密码
    :return: 已分配主键的用户对象
    """
    user: User = User(
        username=username,
        password=password_hash,
        nickname=f"jjtq_{username}",
        bio="这个人很懒，什么都没留下",
    )
    db.add(user)
    # 事务由 get_db 统一提交，flush 仅用于获取自增主键
    await db.flush()
    return user


async def create_user_token(
    db: AsyncSession, user_id: int, token_hash: str, lifetime: timedelta
) -> None:
    """
    保存令牌摘要和过期时间。

    :param db: 数据库异步会话
    :param user_id: 登录用户 ID
    :param token_hash: 令牌的 SHA-256 摘要
    :param lifetime: 令牌有效期
    """
    # 使用数据库时间计算和校验，避免应用与数据库时区不同导致提前过期。
    database_time = (await db.execute(select(func.now()))).scalar_one()
    db.add(
        UserToken(
            user_id=user_id, token=token_hash, expires_at=database_time + lifetime
        )
    )
    await db.flush()


async def get_user_by_valid_token(db: AsyncSession, token_hash: str) -> User | None:
    """
    根据未过期的令牌摘要查询用户。

    :param db: 数据库异步会话
    :param token_hash: 令牌的 SHA-256 摘要
    :return: 对应用户；令牌不存在、已过期或用户不存在时返回 None
    """
    result = await db.execute(
        select(User)
        .join(UserToken, UserToken.user_id == User.id)
        .where(UserToken.token == token_hash, UserToken.expires_at > func.now())
    )
    return result.scalar_one_or_none()


async def update_user_info(
    db: AsyncSession, user: User, fields: dict[str, str | None]
) -> User:
    """
    更新当前用户提供的资料字段。

    :param db: 数据库异步会话
    :param user: 已认证的用户对象
    :param fields: 需要写入的用户资料字段
    :return: 更新后的用户对象
    """
    for field, value in fields.items():
        setattr(user, field, value)
    await db.flush()
    return user


async def update_user_password(
    db: AsyncSession,
    user_id: int,
    old_password_hash: str,
    new_password_hash: str,
) -> bool:
    """
    更新当前用户的密码。

    :param db: 数据库异步会话
    :param user_id: 当前用户 ID
    :param old_password_hash: 用户的旧密码的哈希值
    :param new_password_hash: 用户的新密码的哈希值
    :return: 更新成功时为 True；用户不存在或密码已发生变化时为 False
    """
    result = await db.execute(
        update(User)
        .where(User.id == user_id, User.password == old_password_hash)
        .values(password=new_password_hash)
    )
    await db.flush()
    return cast(CursorResult[Any], result).rowcount == 1


async def delete_user_tokens(db: AsyncSession, user_id: int) -> None:
    """
    删除用户的全部登录令牌。

    :param db: 数据库异步会话
    :param user_id: 需要撤销令牌的用户 ID
    """
    await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
    await db.flush()
