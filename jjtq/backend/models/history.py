from datetime import datetime

from sqlalchemy import Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """模型基类。"""


class History(Base):
    """浏览历史模型，每次浏览保存一条记录。"""

    __tablename__ = "history"
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="历史ID"
    )
    user_id: Mapped[int] = mapped_column(comment="用户ID")
    news_id: Mapped[int] = mapped_column(comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, comment="浏览时间"
    )

    __table_args__ = (
        Index("fk_history_user_idx", "user_id"),
        Index("fk_history_news_idx", "news_id"),
        Index("idx_view_time", view_time.desc()),
    )
