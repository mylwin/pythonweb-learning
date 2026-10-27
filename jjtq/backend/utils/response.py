from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data: Any = None) -> JSONResponse:
    """
    构造统一成功响应。

    :param message: 提示信息
    :param data: 响应数据，支持 FastAPI、Pydantic 和 ORM 对象
    :return: JSON 响应
    """
    content = {"code": 200, "message": message, "data": data}
    return JSONResponse(content=jsonable_encoder(content))


def error_response(status_code: int, message: str, data: Any = None) -> JSONResponse:
    """
    构造统一错误响应，HTTP 状态码与响应体 code 保持一致。

    :param status_code: HTTP 状态码
    :param message: 错误信息
    :param data: 附加错误数据
    :return: JSON 响应
    """
    content = {"code": status_code, "message": message, "data": data}
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
    )
