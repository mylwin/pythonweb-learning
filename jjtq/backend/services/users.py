import uuid

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import users as users_crud
from jjtq.backend.schemas.users import UserAuthResponse, UserInfoResponse


async def register_user(
    db: AsyncSession, username: str, password: str
) -> UserAuthResponse | None:
    """注册用户并生成登录 token。

    :param db: 数据库异步会话
    :param username: 用户名
    :param password: 明文密码，由服务层负责加密
    :return: 认证数据；用户名已存在时返回 None
    """
    if await users_crud.get_user_by_username(db, username) is not None:
        return None

    # 加密密码，数据库中不保存明文
    password_hash: str = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    user = await users_crud.create_user(db, username, password_hash)

    # 生成随机 token
    token: str = uuid.uuid4().hex
    return UserAuthResponse(
        token=token,
        user_info=UserInfoResponse.model_validate(user),
    )
