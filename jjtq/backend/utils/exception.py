from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from jjtq.backend.utils.response import error_response


def validation_error_message(error: dict) -> str:
    """
    将常见的校验错误转换为可读的中文提示。

    :param error: Pydantic 校验错误信息
    :return: 不包含输入值的提示文字
    """
    # 字段
    field = error.get("loc", ())[-1:]
    # 错误类型
    field_key = field[0] if field and isinstance(field[0], str) else ""
    # 字段名称
    field_name = {"username": "用户名", "password": "密码"}.get(field_key, "该字段")
    error_type = error.get("type")
    context = error.get("ctx") or {}
    if error_type == "missing":
        return f"请填写{field_name}"
    if error_type == "string_too_short":
        return f"{field_name}长度不能少于 {context['min_length']} 个字符"
    if error_type == "string_too_long":
        return f"{field_name}长度不能超过 {context['max_length']} 个字符"
    if error_type == "string_type":
        return f"{field_name}必须是字符串"
    if error_type == "value_error":
        return error.get("msg", "输入不符合要求").removeprefix("Value error, ")
    return "输入不符合要求"


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器，统一错误响应格式。

    :param app: FastAPI 应用实例
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        将 HTTPException 转换为统一错误响应。

        :param request: 当前请求
        :param exc: HTTP 异常
        :return: 统一错误响应
        """
        response = error_response(exc.status_code, str(exc.detail))
        # 如果响应头有自定义头，则添加到响应中
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        将请求参数校验异常转换为统一错误响应。

        :param request: 当前请求
        :param exc: 参数校验异常
        :return: 统一错误响应
        """
        errors = [
            {
                "loc": error.get("loc", ()),
                "type": error.get("type", "validation_error"),
                "msg": validation_error_message(error),
            }
            for error in exc.errors()
        ]
        return error_response(422, "请求参数校验失败", errors)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        兜底处理未捕获异常。

        :param request: 当前请求
        :param exc: 未捕获异常
        :return: 统一错误响应
        """
        return error_response(500, "服务器内部错误")
