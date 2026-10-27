from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.users import User


# 根据用户名查询用户
async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# 创建用户
async def create_user(db: AsyncSession, username: str, password_hash: str) -> User:
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
