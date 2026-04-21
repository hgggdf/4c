"""后端应用入口。"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import check_database_health, init_application_database
from app.router.analysis import router as analysis_router
from app.router.announcement import router as announcement_router
from app.router.announcement_write import router as announcement_write_router
from app.router.cache import router as cache_router
from app.router.chat import router as chat_router
from app.router.company import router as company_router
from app.router.company_write import router as company_write_router
from app.router.financial import router as financial_router
from app.router.financial_write import router as financial_write_router
from app.router.ingest import router as ingest_router
from app.router.macro import router as macro_router
from app.router.macro_write import router as macro_write_router
from app.router.maintenance import router as maintenance_router
from app.router.news import router as news_router
from app.router.news_write import router as news_write_router
from app.router.retrieval import router as retrieval_router
from app.router.stock import router as stock_router
from config import get_settings

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
app.include_router(announcement_router)
app.include_router(announcement_write_router)
app.include_router(cache_router)
app.include_router(company_router)
app.include_router(company_write_router)
app.include_router(financial_router)
app.include_router(financial_write_router)
app.include_router(ingest_router)
app.include_router(macro_router)
app.include_router(macro_write_router)
app.include_router(maintenance_router)
app.include_router(news_router)
app.include_router(news_write_router)
app.include_router(retrieval_router)


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时初始化数据库基础结构。"""
    init_application_database()


@app.get("/health")
def health_check(response: Response):
    """返回服务与数据库的基础健康状态。"""
    db_status = check_database_health()
    database_available = db_status.get("available", False)
    overall_status = "ok" if database_available else "degraded"
    if not database_available:
        response.status_code = 503

    return {
        "status": overall_status,
        "service": {
            "name": settings.app_name,
            "status": "alive",
        },
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
