# Bug 记录

## 2026-10-17：test2.py 启动时报 MySQL 数据库不存在

### 问题现象

运行 `study/day02/test2.py` 时，FastAPI 在启动阶段执行建表操作失败，报错如下：

```text
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError)
(1049, "Unknown database 'python_web_study'")
```

MySQL 容器正在运行，镜像为 `mysql:8.0`，容器的 `3306` 端口已映射到宿主机的 `3306` 端口。

### 原因

连接配置指定了 `127.0.0.1:3306` 上的 `python_web_study` 数据库。实际连接验证表明，地址、端口和账号密码可用，但该数据库尚未创建。

`Base.metadata.create_all()` 只会在已有数据库中创建模型对应的表，不会创建数据库。程序在连接目标数据库时就已失败，因此无法执行后续建表操作。

### 解决方法

先连接已有的数据库（本次使用 `mysql` 系统库），执行：

```sql
CREATE DATABASE IF NOT EXISTS `python_web_study`
CHARACTER SET utf8mb4;
```

也可以在终端进入容器中的 MySQL 客户端，按提示输入 root 密码后执行上述 SQL：

```bash
docker exec -it mysql mysql -u root -p
```

创建数据库后，在项目根目录重新运行程序：

```bash
.venv/bin/python study/day02/test2.py
```

本次修复只补建数据库，无需修改 `test2.py` 的连接配置或建表代码。

### 验证结果

已调用应用原有的 FastAPI 生命周期并查询表列表，确认：

- `python_web_study` 数据库创建成功。
- `tb_book`、`tb_user` 两张表及 `ix_tb_user_name` 唯一索引创建成功。
- FastAPI 生命周期启动和关闭均成功。

### 排查要点

`docker ps` 显示容器运行且端口已映射，只能确认容器和端口配置；还需实际连接验证账号权限及目标数据库是否存在。遇到 `1049 Unknown database` 时，应先检查数据库名称和数据库是否已创建。

## 2026-10-17：Depends 参数默认值触发 Ruff B008

### 问题现象与原因

接口使用 `db: AsyncSession = Depends(get_database)` 时，Ruff 提示 `B008: Do not perform function call Depends in argument defaults`。

B008 检查参数默认值中的函数调用，因为默认值在函数定义时求值，多次调用会复用同一个默认值。这里的 `Depends` 是 FastAPI 的依赖声明，并不是直接创建数据库会话；这条提示属于静态检查告警。

### 解决方法

导入 `typing.Annotated`，将依赖声明放入类型注解中：

```python
from typing import Annotated

@app.get("/book/books")
async def get_book_list(db: Annotated[AsyncSession, Depends(get_database)]):
    result: Result = await db.execute(select(Book))
    books = result.scalars().all()
    return books
```

这样参数默认值中不再包含函数调用，同时保留 FastAPI 对 `get_database` 的依赖注入及会话生命周期管理。不要把 `Depends(get_database)` 移到函数体内，它是由 FastAPI 解析的依赖声明。

## 2026-10-17：/book/summary 被当作按 id 查询，返回 422

### 问题现象与原因

请求 `/book/summary` 时，返回 `int_parsing` 错误，错误位置是 `path.id`，输入值为 `summary`。

`/book/{id}` 比 `/book/summary` 更早注册。FastAPI 按路由注册顺序匹配，动态路径先匹配到 `summary`，随后才执行参数的整数校验。函数参数上的 `int` 注解用于校验，不会让路由匹配阶段自动跳过非数字路径；校验失败后也不会继续匹配下一个路由。

### 解决方法

将固定路径注册在同级动态路径之前：

```python
@app.get("/book/books")
async def get_book_list(...):
    ...

@app.get("/book/summary")
async def get_books_count(...):
    ...

@app.get("/book/{id}")
async def get_book_by_id(...):
    ...
```

调整后，`/book/summary` 匹配聚合查询，`/book/books` 匹配列表查询，`/book/1` 仍匹配按编号查询。重启应用后生效。

## 2026-10-17：新增分页接口后再次发生路由冲突

### 问题现象与原因

新增的 `/book/pagination` 注册在 `/book/{id}` 后面，请求时 `pagination` 被当作 `id`，再次触发 `int_parsing` 错误。此前只调整了 `summary` 的位置，未限制动态路由的匹配范围。

### 解决方法

将按编号查询的路由改为：

```python
@app.get("/book/{id:int}")
async def get_book_by_id(
    id: Annotated[int, Path(title="图书编号", description="图书编号", nullable=False)],
    db: Annotated[AsyncSession, Depends(get_database)],
):
    ...
```

`{id:int}` 是路径转换器，会在路由匹配阶段只接受数字；函数参数的 `int` 注解则用于匹配后的校验。这样注册在后面的固定路径也不会被该动态路由拦截。

请求地址仍为 `/book/1`，分页接口使用 `/book/pagination?page=1&size=10`。不存在的非数字路径会返回 404，而不是进入编号参数校验并返回 422。修改后需重启服务。

## 2026-10-17：路由已修改，但应用因新增接口的请求体类型错误而无法重新加载

### 问题现象与原因

代码已使用 `/book/{id:int}`，但 Uvicorn 工作进程退出，重载进程仍占用 8000 端口，实际请求超时。此时看到的旧 422 响应不能用于判断最新代码是否已加载。

直接导入模块发现，新增接口将 SQLAlchemy ORM 类 `Book` 作为请求体参数类型：`add_book(book: Book, ...)`。该类型不是有效的 Pydantic 请求模型，FastAPI 在注册接口时抛出 `Invalid args for response field`，导致整个应用导入失败。

### 解决方法与验证

- 定义独立的 Pydantic `BookCreate` 请求模型，包含 `name`、`author` 和 `price`。
- 使用 `Book(**book.model_dump())` 构造 ORM 对象，保存后返回 ORM 对象。
- 验证模块可导入、OpenAPI 正常生成，新增接口使用 `BookCreate` 请求体。
- Uvicorn 自动重新加载后，实际请求 `/book/pagination?page=1&size=1` 返回 HTTP 200，取得 1 条数据。
