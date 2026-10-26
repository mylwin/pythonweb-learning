from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# 数据库设置
class Settings(BaseSettings):
    ASYNC_DATABASE_URL: str
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env"
    )


# 配置由 BaseSettings 从环境变量或 .env 读取，无需手动传入构造参数
# noinspection PyArgumentList
settings = Settings()  # type: ignore

# 创建异步引擎
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=True,  # 输出 SQL 日志
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 连接池溢出时最大连接数
    pool_recycle=3600,  # 连接池回收时间
    pool_pre_ping=True,  # 连接池预检
    connect_args={"connect_timeout": 10},  # 连接超时时间
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 不自动提交
)


# 依赖项，获取数据库异步会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
