import sys
from pathlib import Path

# 兼容在 backend 目录执行 uvicorn main:app 或直接运行 main.py
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jjtq.backend.routers import news, users

# 创建 app 实例
app = FastAPI(title="掘金头条")

# 绑定路由
app.include_router(news.router)
app.include_router(users.router)

# 解决跨域问题
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 启动服务
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
