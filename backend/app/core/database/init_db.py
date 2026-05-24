"""数据库初始化与健康检查服务（v3）。"""

from __future__ import annotations

from sqlalchemy import text

from app.core.database.base import Base
import app.core.database.models as models  # noqa: F401
from app.core.database.session import SessionLocal, engine


class DatabaseService:
    TABLE_NAMES = [
        "industry_master",
        "company",
        "app_user",
        "watchlist",
        "chat_session",
        "chat_history",
        "financial_hot",
        "financial_archive",
        "announcement_hot",
        "announcement_archive",
        "research_report_hot",
        "research_report_archive",
        "macro_indicator",
        "news_hot",
        "news_archive",
        "vector_document_index",
        "data_job_log",
        "staging_import",
    ]

    def __init__(self) -> None:
        from app.service import ServiceContainer
        self.services = ServiceContainer.build_default()

    def initialize_database(self) -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            company_service = getattr(self.services, "company", None)
            if company_service is not None:
                for method in ("bootstrap_from_local_files", "backfill_structured_tables_from_local_files"):
                    fn = getattr(company_service, method, None)
                    if callable(fn):
                        try:
                            fn(db)
                        except Exception:
                            pass
            self._ensure_demo_user(db)
            db.commit()

    def check_health(self) -> dict:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
                counts = self._get_table_counts(db, self.TABLE_NAMES)
            return {"status": "ok", "tables": counts}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _ensure_demo_user(self, db) -> None:
        from sqlalchemy import select
        from app.core.database.models.user import User
        existing = db.execute(select(User).limit(1)).scalars().first()
        if existing is not None:
            return
        db.add(User(username="demo_user", password_hash="demo_password_hash", role="user", status="active"))
        db.flush()

    def _get_table_counts(self, db, table_names: list[str]) -> dict[str, int | str]:
        counts: dict[str, int | str] = {}
        for table_name in table_names:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                counts[table_name] = int(result or 0)
            except Exception:
                counts[table_name] = "missing"
        return counts


def init_database() -> None:
    DatabaseService().initialize_database()


def check_db_health() -> dict:
    return DatabaseService().check_health()
