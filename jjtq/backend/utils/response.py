from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


# 统一成功响应：把 FastAPI、Pydantic、ORM 对象转换成可 JSON 序列化的结构
def success_response(message: str = "success", data: Any = None) -> JSONResponse:
    content = {"code": 200, "message": message, "data": data}
    return JSONResponse(content=jsonable_encoder(content))


# 统一错误响应，HTTP 状态码与响应体 code 保持一致
def error_response(status_code: int, message: str, data: Any = None) -> JSONResponse:
    content = {"code": status_code, "message": message, "data": data}
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
    )
