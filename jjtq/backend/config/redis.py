from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff


class RedisSettings(BaseSettings):
    """Redis 连接配置，地址中的数据库编号必须为 1。"""

    redis_url: SecretStr = Field(
        default=SecretStr("redis://localhost:6379/1"), validation_alias="REDIS_URL"
    )
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore"
    )


def create_redis_client() -> Redis:
    """
    创建惰性连接的异步 Redis 客户端，连接池由客户端管理。

    :return: 使用数据库 1 的客户端；应用关闭时调用 aclose 释放连接池
    :raises ValueError: 连接地址选择的 Redis 数据库不是 1
    """
    settings = RedisSettings()
    client = Redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,  # 以字符串形式返回而不是字节
        socket_connect_timeout=0.3,  # 连接超时时间，单位秒
        socket_timeout=0.3,  # 读取超时，单位秒
        retry=Retry(NoBackoff(), 0),  # 禁用重试
        max_connections=20,  # 连接池最大连接数
    )
    # URL 查询参数优先于路径，检查最终解析结果以免误用数据库 0。
    if client.connection_pool.connection_kwargs.get("db", 0) != 1:
        raise ValueError("REDIS_URL 必须指定 Redis 数据库 1")
    return client
