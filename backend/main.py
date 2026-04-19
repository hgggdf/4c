from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.stock import router as stock_router
from config import get_settings
from database.init_db import init_database

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


@app.on_event("startup")
def on_startup() -> None:
    init_database()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "database": settings.mysql_database,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
