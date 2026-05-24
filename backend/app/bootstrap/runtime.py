"""应用启动与健康检查适配层。"""

from __future__ import annotations

from sqlalchemy import inspect, select, text

from app.core.database.base import Base
import app.core.database.models as database_models  # noqa: F401
import app.core.database.session as session_runtime
from config import get_settings
EXPECTED_USER_COLUMNS = {"id", "username", "password_hash", "role", "status"}
ACTIVE_STORAGE_MODE = "mysql-only"


def _assert_mysql_runtime() -> None:
    """确保启动适配层只在 MySQL 运行主链上工作。"""
    dialect_name = session_runtime.engine.dialect.name
    if dialect_name != "mysql":
        raise RuntimeError(
            "当前运行模式只支持 MySQL；检测到非 MySQL 数据库连接，应用已阻止启动。"
        )


def _validate_users_schema() -> None:
    """校验已有 users 表是否仍与运行主链兼容。"""
    inspector = inspect(session_runtime.engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return

    try:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "当前运行模式只支持 MySQL；已连接到 MySQL，但 users 表结构校验失败，"
            "应用已阻止启动。"
        ) from exc

    missing_user_columns = sorted(EXPECTED_USER_COLUMNS - user_columns)
    if missing_user_columns:
        raise RuntimeError(
            "当前运行模式只支持 MySQL；已连接到 MySQL，但 users 表缺少关键字段，"
            f"应用已阻止启动。缺失字段：{', '.join(missing_user_columns)}"
        )


_assert_mysql_runtime()


def init_application_database() -> None:
    """初始化数据表，并确保演示用户存在。"""
    _assert_mysql_runtime()
    settings = get_settings()
    Base.metadata.create_all(bind=session_runtime.engine)
    _validate_users_schema()

    with session_runtime.SessionLocal() as db:
        demo_user = db.execute(
            select(database_models.User).where(database_models.User.id == settings.demo_user_id)
        ).scalars().first()
        if demo_user is None:
            username = settings.demo_username
            existing_name = db.execute(
                select(database_models.User).where(database_models.User.username == username)
            ).scalars().first()
            if existing_name is not None and existing_name.id != settings.demo_user_id:
                username = f"{username}_{settings.demo_user_id}"

            db.add(
                database_models.User(
                    id=settings.demo_user_id,
                    username=username,
                    password_hash="demo_password_hash",
                    role="user",
                    status="active",
                )
            )
        db.commit()


def check_database_health() -> dict:
    """返回数据库运行模式与真实连通状态。"""
    try:
        _assert_mysql_runtime()
        database_health = session_runtime.probe_database_connection()
        database_health["storage_mode"] = ACTIVE_STORAGE_MODE
        database_health["runtime_mode"] = ACTIVE_STORAGE_MODE
        database_health["engine"] = (
            f"{session_runtime.engine.dialect.name}+{session_runtime.engine.dialect.driver}"
        )
        return database_health
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "available": False,
            "dialect": session_runtime.engine.dialect.name,
            "driver": session_runtime.engine.dialect.driver,
            "database_name": None,
            "server_version": None,
            "latency_ms": None,
            "storage_mode": ACTIVE_STORAGE_MODE,
            "runtime_mode": ACTIVE_STORAGE_MODE,
            "engine": f"{session_runtime.engine.dialect.name}+{session_runtime.engine.dialect.driver}",
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }