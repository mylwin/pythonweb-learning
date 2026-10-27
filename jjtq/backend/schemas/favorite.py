from pydantic import BaseModel, Field


class FavoriteCheckData(BaseModel):
    """收藏状态数据。"""

    is_favorite: bool = Field(serialization_alias="isFavorite")


class FavoriteCheckResponse(BaseModel):
    """收藏状态接口响应。"""

    code: int = 200
    message: str = "success"
    data: FavoriteCheckData
