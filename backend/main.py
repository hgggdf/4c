"""后端应用入口，负责创建 FastAPI 实例、注册路由并在启动时初始化数据库。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.chat.router import router as chat_router
from modules.stock.router import router as stock_router
from modules.analysis.router import router as analysis_router
from config import get_settings
from core.database.init_db import init_database

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(stock_router)
app.include_router(analysis_router)


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时执行数据库初始化与本地数据导入。"""
    init_database()


@app.get("/health")
def health_check():
    """返回服务与数据库的基础健康状态，供前端和部署环境探活使用。"""
    from core.database.init_db import check_db_health
    db_status = check_db_health()
    return {
        "status": "ok",
        "service": settings.app_name,
        "database": settings.mysql_database,
        "db_health": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
