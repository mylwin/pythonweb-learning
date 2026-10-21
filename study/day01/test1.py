"""
day01 测试代码
"""

import asyncio
import time
from pathlib import Path as PathlibPath
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

# 学习资料目录：study/test_files
ASSETS_DIR = PathlibPath(__file__).resolve().parents[1] / "test_files"


class User(BaseModel):
    """
    用户模型
    """

    id: int = Field(description="用户ID")
    name: str = Field(description="用户名")
    age: int = Field(description="用户年龄")


class BookIn(BaseModel):
    """
    图书请求体模型
    """

    name: str = Field(
        description="图书名称, 不能为空，长度 2——20",
        min_length=2,
        max_length=20,
    )
    author: str = Field(description="图书作者，长度 2-10", min_length=2, max_length=10)
    publisher: str = Field(
        description="图书出版社【默认为黑马初版社】", default="黑马初版社"
    )
    price: float = Field(description="图书价格，不能为空，价格大于 0 元", gt=0)


class BookOut(BookIn):
    """
    图书响应体模型
    """

    id: int = Field(description="图书编号")


def getUser(id: int) -> User:
    """
    获取用户信息
    """
    return User(id=id, name="张三", age=18)


# 创建一个FastAPI实例
app = FastAPI(title="python web day01 测试代码")


@app.get("/sync")
def funcSync():
    """
    同步函数测试接口
    """
    start = time.time()
    for i in range(100):
        time.sleep(0.1)
    end = time.time()
    return {"sync time": f"{end - start:.2f}s"}


@app.get("/async")
async def funcAsync():
    """
    异步函数测试接口
    """
    start = time.time()
    tasks = [asyncio.sleep(0.1) for i in range(100)]
    await asyncio.gather(*tasks)
    end = time.time()
    return {"async time": f"{end - start:.2f}s"}


@app.post("/user")
async def user(user: User):
    """
    创建用户测试接口
    """
    return user


@app.get("/user/hello")
async def hello():
    """
    测试路由接口
    """
    return {"message": "hello world 我正在学习 FastAPI"}


@app.get("/book/{id}")
async def getBook(id: int):
    """
    创建路径参数测试接口
    """
    return {"id": id, "title": f"这是第{id}本书"}


@app.get("/user/{id}")
async def getUserById(id: int):
    """
    创建路径参数练习接口
    """
    user: User = getUser(id)

    return {"id": user.id, "name": user.name, "age": user.age}


@app.get("/news/category/{category_id}")
async def getNewsByCategoryId(
    category_id: Annotated[
        int,
        Path(
            title="新闻分类 Id",
            description="分类 Id，范围 1——100",
            ge=1,
            le=100,
        ),
    ],
):
    """
    创建 Path 参数类型注解练习1接口
    """
    return {"category_id": category_id, "message": f"获取分类 {category_id} 的新闻成功"}


@app.get("/news/category/name/{category_name}")
async def getNewsByCategoryName(
    category_name: Annotated[
        str,
        Path(
            title="新闻分类名称",
            description="分类名称，长度 2——10",
            min_length=2,
            max_length=10,
        ),
    ],
):
    """
    创建 Path 参数类型注解练习2接口
    """
    return {
        "category_name": category_name,
        "message": f"获取分类 {category_name} 的新闻成功",
    }


# 查询参数练习
@app.get("/books")
async def getBooks(
    category: Annotated[
        str,
        Query(
            title="图书分类",
            description="图书分类，长度 5——255",
            min_length=5,
            max_length=255,
        ),
    ],
    price: Annotated[
        float,
        Query(
            title="图书价格",
            description="图书价格，范围 50——100",
            ge=50,
            le=100,
        ),
    ],
):
    return {
        "category": category,
        "price": price,
        "message": f"查询分类为{category}的图书，价格在{price}元的书成功",
    }


# 请求体参数练习
fakeBookDb: dict[int, BookOut] = {}
nextId = 1


@app.post("/books", response_model=BookOut, status_code=201)
def createBook(book: BookIn) -> BookOut:
    """
    新增图书
    """
    global nextId
    # model_dump(): 将模型对象转换为字典
    newBook = BookOut(id=nextId, **book.model_dump())
    fakeBookDb[nextId] = newBook
    nextId += 1
    return newBook


# 测试 HTML 响应格式
@app.get("/html", response_class=HTMLResponse)
async def html():
    """
    返回 HTML
    """
    return """
    <html>
        <head>
            <title>Hello World</title>
        </head>
        <body>
            <h1>Hello World</h1>
        </body>
    </html>
    """


# 测试文件响应格式
@app.get("/file")
async def file():
    """
    返回文件
    """
    filePath = ASSETS_DIR / "test1.png"
    return FileResponse(filePath)


# 测试异常处理
@app.get("/error/{id}")
async def error(
    id: Annotated[
        int, Path(title="用户 ID", description="测试时候 id 只有 1，2，3，4，5")
    ],
):
    idList = [1, 2, 3, 4, 5]
    if id not in idList:
        raise HTTPException(status_code=404, detail="当前 Id 不存在")
    return {"id": id}


# 测试接口
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

    # 在浏览器打开两个接口地址
