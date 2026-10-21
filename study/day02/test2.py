"""
python web day02 代码
"""

from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.params import Query
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, Numeric, Result, String, Table, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ORM 建表流程
#  1.创建数据库引擎
ASYNC_DATEBASE_URL = "mysql+aiomysql://root:123456@127.0.0.1:3306/python_web_study"
asyncEngine: AsyncEngine = create_async_engine(
    ASYNC_DATEBASE_URL,
    echo=True,  # 输出 SQL 日志
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 连接池溢出时最大连接数
)


# 2.定义模型类
# 2.1 创建基类
class Base(DeclarativeBase):
    createTime: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # 服务器默认时间
        default=datetime.now,
        nullable=False,
        comment="创建时间",
    )
    updateTime: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # 服务器默认时间
        default=datetime.now,
        nullable=False,
        comment="更新时间",
    )


# 2.2 创建模型类
class Book(Base):
    __tablename__ = "tb_book"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="图书编号",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="图书名称",
    )
    author: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="图书作者",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
        comment="图书价格（元）",
    )


# 3.创建数据库表
# 3.1 从连接池获取异步链接，开启事务，执行 ORM 操作
async def createTables():
    async with asyncEngine.begin() as conn:
        # 获取 ORM 模型对应的 Table 对象
        bookTable = Book.__table__
        userTable = User.__table__

        # 显示断言，让 Pylance 知道 __table__ 就是 Table
        assert isinstance(bookTable, Table)
        assert isinstance(userTable, Table)

        # 创建指定的数据表
        await conn.run_sync(Base.metadata.create_all, tables=[bookTable, userTable])


# 3.2 FastAPI 启动时创建数据库表
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用生命周期：
    - 启动时创建数据库表
    - 关闭时关闭数据库连接池
    """
    # 创建数据库表
    await createTables()
    # 启动时 yield 后面的代码
    yield
    # 关闭数据库连接池
    await asyncEngine.dispose()


# 创建 FastAPI 对象
app = FastAPI(lifespan=lifespan)


# 中间件定义的简单示例
@app.middleware("http")
async def middleware(request, call_next):
    """
    中间件
    """
    print(f"中间件开始执行------{datetime.now()}")
    response = await call_next(request)
    print(f"中间件结束执行------{datetime.now()}")
    return response


# 创建数据表练习：用户表
class User(Base):
    __tablename__ = "tb_user"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="用户 Id"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True, comment="用户名"
    )
    password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="用户密码(哈希值)"
    )


# 使用 ORM
# 1.创建异步会话工厂
AsyncSessionLocalFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=asyncEngine,  # 绑定数据库引擎
    class_=AsyncSession,  # 使用异步会话
    expire_on_commit=False,  # 不自动提交
)


# 2.依赖项
async def getDataBase():
    async with AsyncSessionLocalFactory() as session:
        try:
            yield session  # 把会话返回给调用方
            await session.commit()  # 提交会话
        except Exception:
            await session.rollback()  # 出异常，回滚会话
            raise
        finally:
            await session.close()  # 关闭会话


# 3.接口
# 3.1 查询
@app.get("/book/books")
async def getBookList(db: Annotated[AsyncSession, Depends(getDataBase)]):
    result: Result = await db.execute(select(Book))
    user = result.scalars().all()
    return user


# 3.2 聚合查询
@app.get("/book/summary")
async def getBooksCount(db: Annotated[AsyncSession, Depends(getDataBase)]):
    # 获取图书数量
    bookCountResult: Result = await db.execute(select(func.count(Book.id)))
    bookCount = bookCountResult.scalar()

    # 获取图书最高 最低 平均价格
    bookLowestPriceResult: Result = await db.execute(select(func.min(Book.price)))
    bookHighestPriceResult: Result = await db.execute(select(func.max(Book.price)))
    bookAveragePriceResult: Result = await db.execute(select(func.avg(Book.price)))
    bookLowestPrice = bookLowestPriceResult.scalar()
    bookHighestPrice = bookHighestPriceResult.scalar()
    bookAveragePrice = bookAveragePriceResult.scalar()

    # 返回
    return {
        "图书数量：": bookCount,
        "图书最低价格：": bookLowestPrice,
        "图书最高价格：": bookHighestPrice,
        "图书平均价格：": bookAveragePrice,
    }


# 3.3 比较判断
# int 路径转换器在匹配阶段限制编号，避免拦截 summary、pagination 等固定路径。
@app.get("/book/{id:int}")
async def getBookById(
    id: Annotated[int, Path(title="图书编号", description="图书编号", nullable=False)],
    db: Annotated[AsyncSession, Depends(getDataBase)],
):
    result: Result = await db.execute(select(Book).where(Book.id == id))
    book = result.scalars().one_or_none
    return book


# 3.4 模糊查询
@app.get("/book")
async def getBooksByName(
    name: Annotated[
        str,
        Query(
            title="图书名称",
            description="图书名称，长度 1——20",
            min_length=1,
            max_length=20,
        ),
    ],
    db: Annotated[AsyncSession, Depends(getDataBase)],
):
    result: Result = await db.execute(
        select(Book).where(Book.name.ilike(f"%{escape_like(name)}%", escape="\\"))
    )
    books = result.scalars().all()
    return books


def escape_like(s: str) -> str:
    """把 LIKE 里的通配符转义成普通字符。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# 3.5 分页查询
@app.get("/book/pagination")
async def getBookPages(
    page: Annotated[int, Query(title="页码", ge=1)],
    size: Annotated[int, Query(title="每页数量", ge=1)],
    db: Annotated[AsyncSession, Depends(getDataBase)],
):
    # 跳过的数据
    skip = (page - 1) * size
    queryResult: Result = await db.execute(select(Book).offset(skip).limit(size))
    books = queryResult.scalars().all()
    return {"data": books}


# 3.6 新增
class BookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="图书名称")
    author: str = Field(min_length=1, max_length=255, description="图书作者")
    price: Decimal = Field(
        ge=0, max_digits=10, decimal_places=2, description="图书价格（元）"
    )


@app.post("/book/add_book")
async def addBook(book: BookCreate, db: Annotated[AsyncSession, Depends(getDataBase)]):
    # 获取 book 的参数
    bookParams = Book(**book.model_dump())
    db.add(bookParams)
    await db.commit()
    return bookParams


# 3.7 更新操作
@app.put("/book/update_book/{id}")
async def updateBook(
    id: Annotated[int, Path(title="图书编号", nullable=False)],
    book: BookCreate,
    db: Annotated[AsyncSession, Depends(getDataBase)],
):
    # 1.查询数据
    oldBook = await db.get(Book, id)
    if oldBook is None:
        raise HTTPException(status_code=404, detail="图书不存在")

    # 2.修改
    oldBook.name = book.name
    oldBook.author = book.author
    oldBook.price = book.price

    # 3.提交
    await db.commit()
    return oldBook


# 3.8 删除操作
@app.delete("/books/delete_book/{id}")
async def deleteBook(
    id: Annotated[int, Path(title="图书编号", nullable=False)],
    db: Annotated[AsyncSession, Depends(getDataBase)],
):
    # 1.查询
    oldBook = await db.get(Book, id)
    if oldBook is None:
        raise HTTPException(status_code=404, detail="图书不存在")

    # 2.删除
    await db.delete(oldBook)
    await db.commit()

    # 3.返回
    return {"message": f"删除成功: {oldBook.name}"}


# 执行测试
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
