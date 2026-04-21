"""数据库连接与会话管理模块，统一提供 engine、SessionLocal 和依赖注入入口。"""

from collections.abc import Generator
from time import perf_counter

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()


def _runtime_mode_error(message: str) -> RuntimeError:
    return RuntimeError(
        f"当前运行模式只支持 MySQL；{message}"
    )


def _build_engine():
    """构建运行主链与脚本链共用的 MySQL engine。"""
    try:
        database_url = settings.database_url
    except ValueError as exc:
        raise _runtime_mode_error(
            f"数据库连接配置校验失败，应用已阻止启动。{exc}"
        ) from exc

    try:
        backend_name = make_url(database_url).get_backend_name()
    except Exception as exc:  # noqa: BLE001
        raise _runtime_mode_error(
            "数据库连接串无法解析，应用已阻止启动。"
        ) from exc
    if backend_name != "mysql":
        raise _runtime_mode_error(
            "检测到非 MySQL 数据库配置，应用已阻止启动。"
        )

    primary_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    try:
        with primary_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise _runtime_mode_error(
            "无法连接到配置的 MySQL 数据库，应用已阻止启动。"
            "请检查 MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、"
            "MYSQL_DATABASE 或 DATABASE_URL_OVERRIDE。"
        ) from exc
    return primary_engine


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def probe_database_connection() -> dict:
    """返回数据库运行时真实可用性与连接信息。"""
    started_at = perf_counter()
    health = {
        "status": "error",
        "available": False,
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
        "database_name": None,
        "server_version": None,
        "latency_ms": None,
        "error": None,
    }

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT DATABASE() AS current_database, VERSION() AS server_version")
            ).mappings().one()
            health.update(
                {
                    "status": "ok",
                    "available": True,
                    "database_name": row["current_database"],
                    "server_version": row["server_version"],
                    "latency_ms": round((perf_counter() - started_at) * 1000, 2),
                }
            )
    except Exception as exc:  # noqa: BLE001
        health["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    return health


def get_db() -> Generator[Session, None, None]:
    """为 FastAPI 提供请求级数据库会话，并在请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
