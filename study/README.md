# 学习阶段（study）

这里放 FastAPI / SQLAlchemy 学习阶段的练习代码与笔记，和业务项目 `jjtq/` 平级，
方便把「学习」和「业务」分开，不再混在 `src/python_web/` 里。

## 目录结构

```text
study/
├── day01/
│   └── test1.py        # FastAPI 基础：路由、路径/查询参数、请求体、响应类型、异常处理
├── day02/
│   └── test2.py        # SQLAlchemy 异步 ORM：建表、增删改查、分页、依赖注入
├── docs/
│   ├── bug记录.md      # 踩坑记录：数据库不存在、B008、动态路由顺序等
│   ├── tb_book_add_price.sql
│   ├── tb_book_mock_100.sql
│   └── tb_user_mock_100.sql
└── test_files/
    └── test1.png       # test1.py 文件响应接口的示例资源
```

## 运行方式

在仓库根目录执行（依赖由根目录 `pyproject.toml` 统一管理）：

```bash
uv sync

# day01：FastAPI 基础练习，启动后访问 http://127.0.0.1:8000/docs
.venv/bin/python study/day01/test1.py

# day02：SQLAlchemy + MySQL 练习（需要本地 MySQL，准备步骤见 docs/bug记录.md）
.venv/bin/python study/day02/test2.py
```

两个脚本默认都监听 `127.0.0.1:8000`，同一时间只能运行一个。

## 说明

- `test1.py` / `test2.py` 是可独立运行的演示脚本，不是 pytest 用例。
- 静态资源通过 `Path(__file__)` 定位，不依赖启动时的工作目录。
- 表结构变更和 Mock 数据都在 `docs/` 下，属于学习阶段的练习数据。
