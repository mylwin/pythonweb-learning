from sqlalchemy import delete, func, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.models.history import History
from jjtq.backend.models.news import News


async def add(db: AsyncSession, user_id: int, news_id: int) -> History:
    """
    新增一次浏览记录，浏览时间由数据库生成。

    :param db: 数据库异步会话，事务由 get_db 统一提交或回滚
    :param user_id: 已认证用户 ID
    :param news_id: 已由业务层校验存在的新闻 ID
    :return: 新增的历史记录，包含历史记录 ID 和浏览时间
    """
    history = History(user_id=user_id, news_id=news_id)
    db.add(history)
    await db.flush()
    await db.refresh(history)
    return history


async def get_list(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> list[RowMapping]:
    """
    分页查询当前用户浏览过的有效新闻及最近浏览时间。

    :param db: 数据库异步会话
    :param user_id: 当前用户 ID
    :param page: 页码，从 1 开始
    :param page_size: 每页不同新闻数量
    :return: 新闻摘要及最近浏览时间，无有效记录或超出页数时返回空列表
    """
    # 先按新闻归并再分页，重复浏览不会占用多个分页位置。
    recent_history = (
        select(
            History.news_id,
            func.max(History.view_time).label("view_time"),
            func.max(History.id).label("history_id"),
        )
        .where(History.user_id == user_id)
        .group_by(History.news_id)
        .subquery()
    )
    # 时间相同时按每组唯一的历史记录 ID 排序，保证分页顺序稳定。
    statement = (
        select(
            News.id, News.title, News.description, News.image, News.author,
            News.publish_time, News.category_id, News.views,
            recent_history.c.view_time,
        )
        .join(recent_history, recent_history.c.news_id == News.id)
        .order_by(recent_history.c.view_time.desc(), recent_history.c.history_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(statement)
    return list(result.mappings().all())


async def get_count(db: AsyncSession, user_id: int) -> int:
    """
    统计当前用户浏览过且仍存在的不同新闻数量。

    :param db: 数据库异步会话
    :param user_id: 当前用户 ID
    :return: 与列表筛选口径一致的去重总数，无有效记录时返回 0
    """
    result = await db.execute(
        select(func.count(func.distinct(History.news_id)))
        .join(News, News.id == History.news_id)
        .where(History.user_id == user_id)
    )
    return result.scalar_one()


async def remove(db: AsyncSession, user_id: int, news_id: int) -> None:
    """
    删除当前用户对指定新闻的全部浏览记录。

    :param db: 数据库异步会话，事务由 get_db 统一提交或回滚
    :param user_id: 当前用户 ID，限制删除范围
    :param news_id: 新闻 ID，对应记录不存在时不报错
    """
    await db.execute(
        delete(History).where(History.user_id == user_id, History.news_id == news_id)
    )


async def clear(db: AsyncSession, user_id: int) -> None:
    """
    清空当前用户全部浏览记录，包括新闻已删除的残留记录。

    :param db: 数据库异步会话，事务由 get_db 统一提交或回滚
    :param user_id: 当前用户 ID，其他用户的记录不受影响
    """
    await db.execute(delete(History).where(History.user_id == user_id))
