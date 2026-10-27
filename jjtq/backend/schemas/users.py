from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegisterRequest(BaseModel):
    """用户注册请求模型"""

    username: str = Field(min_length=2, max_length=50, description="用户名")
    password: str = Field(min_length=6, max_length=72, description="密码")

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """校验密码是否超过 bcrypt 的 72 字节上限。

        :param value: 原始密码
        :return: 校验通过的密码
        :raises ValueError: 密码 UTF-8 编码后超过 72 字节
        """
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过 72 字节")
        return value


class UserInfoResponse(BaseModel):
    """用户信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None


class UserAuthResponse(BaseModel):
    """用户认证数据，接口使用驼峰字段名"""

    model_config = ConfigDict(from_attributes=True)

    token: str
    user_info: UserInfoResponse = Field(serialization_alias="userInfo")
