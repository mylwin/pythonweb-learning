from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.config.database import get_db
from jjtq.backend.crud import news as news_crud
from jjtq.backend.schemas.news import CategoryListResponse, NewsDetailResponse
from jjtq.backend.services import news as news_service
from jjtq.backend.utils.response import success_response

# 创建 router 实例
router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories", response_model=CategoryListResponse)
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=0)] = 100,
):
    """
    获取新闻分类列表。

    :param db: 数据库异步会话
    :param skip: 跳过的记录数
    :param limit: 返回的记录数上限
    :return: 统一成功响应
    """
    categories = await news_crud.get_categories(db, skip=skip, limit=limit)
    return success_response(data=categories)


@router.get("/list")
async def get_news_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=10, le=100)] = 10,
    category_id: Annotated[int | None, Query(alias="categoryId")] = None,
):
    """
    获取新闻列表。

    :param db: 数据库异步会话
    :param page: 页码，从 1 开始
    :param page_size: 每页记录数，对应查询参数 pageSize
    :param category_id: 分类 ID，对应查询参数 categoryId
    :return: 统一成功响应
    """
    news_list = await news_crud.get_news_list(
        db, page=page, page_size=page_size, category_id=category_id
    )
    return success_response(data={"list": news_list})


@router.get("/detail", response_model=NewsDetailResponse)
async def get_news_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    news_id: Annotated[int, Query(alias="id", title="新闻编号", ge=1)],
):
    """
    获取新闻详情。

    :param db: 数据库异步会话
    :param news_id: 新闻 ID，对应查询参数 id
    :return: 统一成功响应；新闻不存在时返回 404 错误响应
    """
    news_detail = await news_service.get_news_detail(db, news_id)
    return success_response(data=news_detail)
