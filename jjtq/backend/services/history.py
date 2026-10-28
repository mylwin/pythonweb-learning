from sqlalchemy.ext.asyncio import AsyncSession

from jjtq.backend.crud import history as history_crud
from jjtq.backend.crud import news as news_crud
from jjtq.backend.models.users import User
from jjtq.backend.schemas.history import (
    HistoryAddData,
    HistoryListData,
    HistoryListInfoData,
)
from jjtq.backend.utils.errors import BusinessError


async def add_history(
    db: AsyncSession, current_user: User, news_id: int
) -> HistoryAddData:
    """
    为当前用户记录一次有效新闻浏览。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param news_id: 浏览的新闻 ID，写入前校验新闻是否存在
    :return: 新增的浏览记录数据，id 为历史记录 ID，view_time 为数据库时间
    :raises BusinessError: 新闻不存在时抛出 404 业务异常
    """
    if await news_crud.get_news_detail(db, news_id) is None:
        raise BusinessError(404, "新闻不存在")
    # 浏览量由新闻详情接口维护，此处只记录浏览事件，避免重复累加。
    history = await history_crud.add(db, current_user.id, news_id)
    return HistoryAddData(
        id=history.id, user_id=current_user.id,
        news_id=history.news_id, view_time=history.view_time,
    )


async def get_history_list(
    db: AsyncSession, current_user: User, page: int, page_size: int
) -> HistoryListData:
    """
    组装当前用户按新闻去重的浏览历史及分页信息。

    :param db: 数据库异步会话
    :param current_user: 已认证用户
    :param page: 页码，从 1 开始
    :param page_size: 每页不同新闻数量
    :return: 当前页新闻摘要、有效新闻总数和是否还有下一页；无记录时列表为空
    """
    rows = await history_crud.get_list(db, current_user.id, page, page_size)
    total = await history_crud.get_count(db, current_user.id)
    return HistoryListData(
        data_list=[HistoryListInfoData.model_validate(row) for row in rows],
        total=total,
        has_more=page * page_size < total,
    )


async def remove_history(db: AsyncSession, current_user: User, news_id: int) -> None:
    """
    删除当前用户对指定新闻的全部历史，不存在时也视为成功。

    :param db: 数据库异步会话
    :param current_user: 已认证用户，仅删除该用户的记录
    :param news_id: 新闻 ID，即历史列表项中的 id，不是历史记录 ID
    """
    await history_crud.remove(db, current_user.id, news_id)


async def clear_history(db: AsyncSession, current_user: User) -> None:
    """
    清空当前用户历史，重复清空仍视为成功。

    :param db: 数据库异步会话
    :param current_user: 已认证用户，仅清空该用户的记录
    """
    await history_crud.clear(db, current_user.id)
