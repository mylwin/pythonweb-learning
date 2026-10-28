from datetime import datetime

from pydantic import BaseModel, Field


class FavoriteCheckData(BaseModel):
    """收藏状态数据。"""

    is_favorite: bool = Field(serialization_alias="isFavorite")


class FavoriteCheckResponse(BaseModel):
    """收藏状态接口响应。"""

    code: int = 200
    message: str = "success"
    data: FavoriteCheckData


class FavoriteAddData(BaseModel):
    """添加收藏响应数据。"""

    id: int
    user_id: int = Field(serialization_alias="userId")
    news_id: int = Field(serialization_alias="newsId")
    create_time: datetime = Field(serialization_alias="createTime")


class FavoriteAddResponse(BaseModel):
    """添加收藏接口响应。"""

    code: int = 200
    message: str = "success"
    data: FavoriteAddData


class FavoriteRemoveResponse(BaseModel):
    """移除收藏接口响应。"""

    code: int = 200
    message: str = "success"
    data: None
