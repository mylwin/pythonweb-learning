from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# 数据库设置
class Settings(BaseSettings):
    async_database_url: str = Field(validation_alias="ASYNC_DATABASE_URL")
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env"
    )


# 配置由 BaseSettings 从环境变量或 .env 读取，无需手动传入构造参数
# noinspection PyArgumentList
settings = Settings()  # type: ignore

# 创建异步引擎
async_engine = create_async_engine(
    settings.async_database_url,
    echo=True,  # 输出 SQL 日志
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 连接池溢出时最大连接数
    pool_recycle=3600,  # 连接池回收时间
    pool_pre_ping=True,  # 连接池预检
    connect_args={
        "connect_timeout": 10,
        # 每个新连接固定为北京时间；TIMESTAMP 和 NOW() 使用同一会话时区。
        "init_command": "SET time_zone = '+08:00'",
    },
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后保留已加载的属性
)


async def get_db():
    """
    获取数据库异步会话，统一提交和回滚事务。

    :return: 数据库异步会话
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
