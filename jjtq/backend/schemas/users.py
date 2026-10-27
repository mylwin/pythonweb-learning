from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserAuthRequest(BaseModel):
    """用户注册和登录请求模型"""

    username: str = Field(min_length=2, max_length=50, description="用户名")
    password: str = Field(min_length=6, max_length=72, description="密码")

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """
        校验密码是否超过 bcrypt 的 72 字节上限。

        :param value: 原始密码
        :return: 校验通过的密码
        :raises ValueError: 密码 UTF-8 编码后超过 72 字节
        """
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过 72 字节")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """
        校验用户名包含的字符。

        :param value: 原始用户名
        :return: 校验通过的用户名
        :raises ValueError: 用户名不符合要求
        """
        if not value.isalnum():
            raise ValueError("用户名只能包含字母或数字（支持中文）")
        return value


class UserUpdateRequest(BaseModel):
    """用户更新信息请求模型"""

    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(
        default=None, min_length=2, max_length=50, description="昵称"
    )
    avatar: str | None = Field(
        default=None, min_length=2, max_length=255, description="头像"
    )
    gender: Literal["male", "female", "unknown"] | None = Field(
        default=None, description="性别"
    )
    phone: str | None = Field(
        default=None, pattern=r"^1[3-9][0-9]{9}$", description="手机号"
    )
    bio: str | None = Field(
        default=None, min_length=2, max_length=255, description="简介"
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> "UserUpdateRequest":
        """
        检查请求中是否包含至少一个更新字段。

        :return: 包含更新字段的请求模型
        :raises ValueError: 未提供更新字段
        """
        if not self.model_fields_set:
            raise ValueError("请至少提供一个需要更新的字段")
        return self


class UserRegisterInfoResponse(BaseModel):
    """用户注册信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None


class UserLoginInfoResponse(BaseModel):
    """用户登录信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    bio: str | None = None
    nickname: str | None = None
    avatar: str | None = None


class UserRegisterResponse(BaseModel):
    """用户注册响应模型"""

    model_config = ConfigDict(from_attributes=True)

    token: str
    user_info: UserRegisterInfoResponse = Field(serialization_alias="userInfo")


class UserLoginResponse(BaseModel):
    """用户登录响应模型"""

    model_config = ConfigDict(from_attributes=True)

    token: str
    user_info: UserLoginInfoResponse = Field(serialization_alias="userInfo")


class UserProfileUpdateResponse(BaseModel):
    """用户更新信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str | None = None
    avatar: str | None = None
    gender: str | None = None
    bio: str | None = None
