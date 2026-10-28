from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoryAddRequest(BaseModel):
    """新增浏览记录的请求体，用户与浏览时间均由服务端确定。"""

    model_config = ConfigDict(extra="forbid")

    news_id: int = Field(alias="newsId", ge=1)


class HistoryAddData(BaseModel):
    """新增浏览记录数据。"""

    id: int
    user_id: int = Field(serialization_alias="userId")
    news_id: int = Field(serialization_alias="newsId")
    view_time: datetime = Field(serialization_alias="viewTime")


class HistoryAddResponse(BaseModel):
    """新增浏览记录接口响应。"""

    code: int = 200
    message: str = "success"
    data: HistoryAddData


class HistoryListRequest(BaseModel):
    """浏览历史分页查询参数。"""

    page: int = Field(1, ge=1, title="页码")
    page_size: int = Field(50, ge=1, le=100, alias="pageSize", title="每页数量")


class HistoryListInfoData(BaseModel):
    """新闻摘要及最近浏览时间，id 为新闻 ID。"""

    id: int
    title: str
    description: str | None = None
    image: str | None = None
    author: str | None = None
    publish_time: datetime = Field(serialization_alias="publishTime")
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    view_time: datetime = Field(serialization_alias="viewTime")


class HistoryListData(BaseModel):
    """按新闻去重后的浏览历史及分页信息。"""

    data_list: list[HistoryListInfoData] = Field(serialization_alias="list")
    total: int
    has_more: bool = Field(serialization_alias="hasMore")


class HistoryListResponse(BaseModel):
    """浏览历史列表接口响应。"""

    code: int = 200
    message: str = "success"
    data: HistoryListData


class HistoryDeleteResponse(BaseModel):
    """删除或清空浏览历史的接口响应。"""

    code: int = 200
    message: str = "success"
    data: None
