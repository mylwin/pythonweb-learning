from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryData(BaseModel):
    """新闻分类数据模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    name: str
    sort_order: int


class CategoryListResponse(BaseModel):
    """新闻分类列表响应模型"""

    code: int = 200
    message: str = "success"
    data: list[CategoryData]


class RelatedNewsData(BaseModel):
    """相关新闻摘要"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    image: str | None


class NewsDetailData(BaseModel):
    """新闻详情数据，接口使用驼峰字段名"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    image: str | None
    author: str | None
    publish_time: datetime = Field(serialization_alias="publishTime")
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    related_news: list[RelatedNewsData] = Field(
        default_factory=list, serialization_alias="relatedNews"
    )


class NewsDetailResponse(BaseModel):
    """新闻详情接口响应"""

    code: int = 200
    message: str = "success"
    data: NewsDetailData
