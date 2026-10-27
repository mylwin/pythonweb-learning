from datetime import datetime

from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """模型基类"""


class Favorite(Base):
    """收藏模型"""

    __tablename__ = "favorite"
    __table_args__ = (UniqueConstraint("user_id", "news_id", name="user_news_unique"),)

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="收藏ID"
    )
    user_id: Mapped[int] = mapped_column(comment="用户ID")
    news_id: Mapped[int] = mapped_column(comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, comment="创建时间"
    )
