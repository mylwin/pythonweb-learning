class BusinessError(Exception):
    """表示需要回滚事务并返回统一错误响应的业务异常。"""

    def __init__(self, status_code: int, message: str) -> None:
        """
        创建业务异常。

        :param status_code: 对应的 HTTP 状态码
        :param message: 可返回给客户端的错误信息
        """
        super().__init__(message)
        self.status_code = status_code
        self.message = message
