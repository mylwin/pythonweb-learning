from fastapi import Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    """
    获取应用生命周期管理的 Redis 客户端。

    :param request: 当前 HTTP 请求，用于访问应用状态
    :return: 与应用共享连接池的 Redis 客户端
    """
    return request.app.state.redis_client
