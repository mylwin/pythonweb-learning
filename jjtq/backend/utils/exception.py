from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from jjtq.backend.utils.response import error_response


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，统一错误响应格式。

    :param app: FastAPI 应用实例
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """将 HTTPException 转换为统一错误响应。

        :param request: 当前请求
        :param exc: HTTP 异常
        :return: 统一错误响应
        """
        return error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """将请求参数校验异常转换为统一错误响应。

        :param request: 当前请求
        :param exc: 参数校验异常
        :return: 统一错误响应
        """
        return error_response(422, "请求参数校验失败", exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """兜底处理未捕获异常。

        :param request: 当前请求
        :param exc: 未捕获异常
        :return: 统一错误响应
        """
        return error_response(500, "服务器内部错误")
