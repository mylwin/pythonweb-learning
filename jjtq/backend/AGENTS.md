# 后端开发约定

本文件适用于 `jjtq/backend/` 及其所有子目录。

## 目录与文件

- `main.py`：应用入口、中间件与路由注册。
- `config/database.py`：数据库配置、异步引擎、会话工厂及会话依赖。
- `models/`：SQLAlchemy 表模型。
- `schemas/`：Pydantic 请求、响应模型。
- `crud/`：数据库查询和写入，不处理 HTTP 响应。
- `services/`：跨查询的业务编排，例如详情查询、浏览量更新和推荐组合。
- `routers/`：路由声明、参数校验、依赖注入和 HTTP 响应。
- `utils/`：跨模块复用的工具；`response.py` 提供统一的成功与错误响应。
- `tests/`：`test_*.py` 自动化测试和按业务命名的 `.http` 请求示例。
- Python 包目录保留 `__init__.py`；只在需要公开包接口时添加导出。
- 同一业务在各层使用相同文件名，如 `models/news.py`、`crud/news.py`。
  不再添加 `_model`、`_crud`、`_service`、`_routers` 后缀。
- 用户业务统一使用 `users.py`；保留各层现有用户模块，即使当前为空也不删除。
  其他新模块按需创建，不预建空模块或空工具目录。
- 新业务沿用现有分层；当前规模无需再增加抽象层。

## 命名与导入

- Python 文件、函数、参数及普通变量使用 `snake_case`。
- 类名使用 `PascalCase`，真正的常量使用 `UPPER_SNAKE_CASE`。
- 工厂对象使用明确的小写名称，例如 `async_session_factory`。
- 配置对象属性使用小写，环境变量名称保持大写，通过字段别名映射。
- 函数名表达动作和业务对象，例如 `get_news_list`、`get_news_detail`。
- 业务参数使用 `news_id`、`category_id`、`page_size`；避免用 `id`、
  `list` 等内置名称作局部变量或函数参数。模型的 `id` 字段可以保留。
- 时间属性与已有数据库列统一，如 `created_at`、`updated_at`。
- 可空类型统一使用 `str | None`，函数声明尽量补齐参数和返回类型。
- 项目内部使用 `jjtq.backend...` 绝对导入；按标准库、第三方、项目模块
  分组。不同层的同名模块用职责别名区分，例如：

  ```python
  from jjtq.backend.crud import news as news_crud
  from jjtq.backend.services import news as news_service
  ```

## 接口与数据库兼容

- 内部命名调整不改变已有 URL、HTTP 方法、请求参数或响应字段。
- 接口保留既有 `pageSize`、`categoryId`、`id` 等参数，通过
  `Query(alias=...)` 映射到 Python 蛇形参数。
- 响应中的 `publishTime`、`categoryId`、`relatedNews` 使用 Schema
  序列化别名；分类接口现有的 `created_at` 等字段保持原样。
- 成功响应沿用 `code`、`message`、`data`；错误同时使用正确的 HTTP 状态码。
- SQLAlchemy 模型应对应实际数据库表和列，命名整理不得擅自改表结构。
- 数据库访问使用异步会话；调用异步函数必须 `await`。
- 事务由 `get_db` 统一提交和回滚；CRUD 与 Service 不单独提交。
- 浏览量等计数使用数据库原子更新；分页排序包含唯一键以保证顺序稳定。
- `.env` 和真实凭据不得提交；环境文件路径相对源码定位，避免依赖启动目录。

## 验证与文档

- 从仓库根目录执行：

  ```bash
  uv run python -m unittest discover -s jjtq/backend/tests -v
  uv run uvicorn jjtq.backend.main:app --reload
  ```

- 保持在 `backend` 目录执行 `uv run uvicorn main:app --reload` 的兼容性。
- 重命名文件时同步修改导入、测试 mock 路径、文档和 HTTP 请求示例。
- 修改查询、事务或接口行为时运行相关测试；避免只测试实现细节。
- 纯命名重构也要验证应用导入和接口参数、响应契约保持兼容。
- 接口文档放在 `jjtq/docs/`；后端 HTTP 请求示例放在 `tests/`。
- 注释和文档默认使用简体中文，解释业务原因，避免重复代码字面含义。
