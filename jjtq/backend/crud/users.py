from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.users import User


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """根据用户名查询用户。

    :param db: 数据库异步会话
    :param username: 用户名
    :return: 用户对象，不存在时返回 None
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password_hash: str) -> User:
    """创建用户并加入当前事务。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password_hash: bcrypt 加密后的密码
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
