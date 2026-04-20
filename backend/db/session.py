"""数据库连接与会话管理模块，统一提供 engine、SessionLocal 和依赖注入入口。"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()


def _build_engine():
    """优先连接 MySQL，失败时自动回退到本地 SQLite。"""
    primary_engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    try:
        with primary_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary_engine
    except Exception:
        return create_engine(
            settings.sqlite_database_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            pool_recycle=3600,
        )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """为 FastAPI 提供请求级数据库会话，并在请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
