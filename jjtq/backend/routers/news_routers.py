from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import news_crud
from jjtq.backend.config.db_config import get_db
from jjtq.backend.schemas.news import CategoryListResponse, NewsDetailResponse
from jjtq.backend.services import news_service

# 创建 router 实例
router = APIRouter(prefix="/api/news", tags=["news"])


# 获取新闻分类列表
@router.get("/categories", response_model=CategoryListResponse)
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=0)] = 100,
):
    categories = await news_crud.get_categories(db, skip=skip, limit=limit)
    return {"code": 200, "message": "success", "data": categories}


# 获取新闻列表
@router.get("/list")
async def get(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=10, le=100)] = 10,
    category_id: Annotated[int | None, Query(alias="categoryId")] = None,
):
    news_list = await news_crud.get_news(
        db, page=page, pageSize=page_size, category_id=category_id
    )
    return {"code": 200, "message": "success", "data": {"list": news_list}}


# 获取新闻详情
@router.get("/detail", response_model=NewsDetailResponse)
async def get_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: Annotated[int, Query(title="新闻编号", ge=1)],
):
    news_detail = await news_service.get_news_detail(db, id)
    if news_detail is None:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "新闻不存在", "data": None},
        )
    return {"code": 200, "message": "success", "data": news_detail}
