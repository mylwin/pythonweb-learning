from datetime import datetime

from sqlalchemy import VARCHAR, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """模型基类"""


class Category(Base):
    """新闻分类模型"""

    # 表名
    __tablename__ = "news_category"

    # 创建索引：提升查询速度
    __table_args__ = (
        # 创建索引
        Index("fk_news_category_idx", "id"),
        Index("fk_news_category_name_idx", "name"),
    )

    # 字段
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="分类ID"
    )
    name: Mapped[str] = mapped_column(
        VARCHAR(50), nullable=False, comment="分类名称"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序序号"
    )
    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        server_default=func.now(),  # 默认值：当前时间
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        server_default=func.now(),  # 默认值：当前时间
        nullable=False,
        comment="更新时间",
    )


class News(Base):
    """新闻模型"""

    # 表名
    __tablename__ = "news"

    # 创建索引：提升查询速度
    __table_args__ = (
        # 创建索引
        Index("fk_news_category_idx", "category_id"),
        Index("idx_publish_time", "publish_time"),
    )

    # 字段
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="新闻ID"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[str | None] = mapped_column(
        String(500), comment="新闻简介"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[str | None] = mapped_column(
        String(255), comment="封面图片URL"
    )
    author: Mapped[str | None] = mapped_column(
        String(50), comment="作者"
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_category.id"), nullable=False, comment="分类ID"
    )
    views: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="浏览量"
    )
    publish_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="发布时间"
    )

    def __repr__(self) -> str:
        """
        返回新闻对象的调试信息。

        :return: 调试字符串
        """
        return f"<News(id={self.id}, title='{self.title}', views={self.views})>"
