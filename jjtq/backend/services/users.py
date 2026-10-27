import uuid

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.schemas.users import UserInfo, UserRegisterData


# 用户注册：用户名已存在时返回 None
async def register_user(
    db: AsyncSession, username: str, password: str
) -> UserRegisterData | None:
    if await users_crud.get_user_by_username(db, username) is not None:
        return None

    # 加密密码，数据库中不保存明文
    password_hash: str = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    user = await users_crud.create_user(db, username, password_hash)

    # 生成随机 token
    token: str = uuid.uuid4().hex
    return UserRegisterData(
        token=token,
        user_info=UserInfo.model_validate(user),
    )
