from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """模型基类"""


class User(Base):
    """用户模型"""

    __tablename__ = "user"

    # 字段
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用户ID"
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户名"
    )
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像")
    gender: Mapped[str | None] = mapped_column(String(10), comment="性别")
    bio: Mapped[str | None] = mapped_column(String(255), comment="简介")
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, comment="手机号")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="更新时间"
    )


class UserToken(Base):
    """用户令牌模型。"""

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
