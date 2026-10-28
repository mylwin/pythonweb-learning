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


class FavoriteListRequest(BaseModel):
    """收藏列表请求参数。"""

    page: int = Field(1, ge=1, title="页码")
    page_size: int = Field(10, ge=1, le=100, title="每页数量", alias="pageSize")


class FavoriteListInfoData(BaseModel):
    """
    收藏列表信息数据。
    """

    id: int
    title: str
    description: str | None = None
    image: str | None = None
    author: str | None = None
    publish_time: datetime = Field(serialization_alias="publishTime")
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    favorite_time: datetime = Field(serialization_alias="favoriteTime")


class FavoriteListData(BaseModel):
    """收藏列表数据。"""

    data_list: list[FavoriteListInfoData] = Field(
        default_factory=list, serialization_alias="list"
    )
    total: int
    has_more: bool = Field(serialization_alias="hasMore")


class FavoriteListResponse(BaseModel):
    """收藏列表接口响应。"""

    code: int = 200
    message: str = "success"
    data: FavoriteListData


class FavoriteClearResponse(BaseModel):
    """清空收藏接口响应。"""

    code: int = 200
    message: str = "success"
    data: None
