import hashlib
import secrets

import bcrypt
from fastapi.concurrency import run_in_threadpool


def create_token() -> str:
    """生成 128 位随机令牌。"""
    return secrets.token_hex(16)


def hash_token(token: str) -> str:
    """
    计算令牌摘要以供数据库保存和查询。

    :param token: 客户端持有的随机令牌
    :return: SHA-256 十六进制摘要
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


async def hash_password(password: str) -> str:
    """
    使用随机盐对密码执行 bcrypt 哈希。

    :param password: 待哈希的明文密码
    :return: 包含算法参数和盐的 bcrypt 哈希
    """
    def create_hash() -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    return await run_in_threadpool(create_hash)


async def verify_password(password: str, password_hash: str) -> bool:
    """
    使用存储的 bcrypt 哈希验证密码。

    :param password: 用户输入的明文密码
    :param password_hash: 数据库中保存的 bcrypt 哈希
    :return: 密码匹配时为 True，哈希无效或密码不匹配时为 False
    """
    def check_hash() -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except (ValueError, TypeError, UnicodeError):
            return False

    return await run_in_threadpool(check_hash)
