"""数据库初始化与健康检查服务。"""

from __future__ import annotations

from sqlalchemy import text

from app.core.database.base import Base
import app.core.database.models as models  # noqa: F401
from app.core.database.session import SessionLocal, engine


class DatabaseService:
    """封装建表、演示数据初始化和健康检查逻辑。"""

    TABLE_NAMES = [
        "company_master",
        "company_profile",
        "industry_master",
        "company_industry_map",
        "users",
        "chat_session",
        "chat_message",
        "watchlist",
        "income_statement_hot",
        "balance_sheet_hot",
        "cashflow_statement_hot",
        "financial_metric_hot",
        "financial_notes_hot",
        "business_segment_hot",
        "stock_daily_hot",
        "announcement_raw_hot",
        "announcement_structured_hot",
        "drug_approval_hot",
        "clinical_trial_event_hot",
        "centralized_procurement_event_hot",
        "regulatory_risk_event_hot",
        "macro_indicator_hot",
        "news_raw_hot",
        "news_structured_hot",
        "news_industry_map_hot",
        "news_company_map_hot",
        "industry_impact_event_hot",
        "query_result_cache",
        "hot_data_cache",
        "session_context_cache",
        "report_preview_cache",
    ]

    def __init__(self) -> None:
        from app.service import ServiceContainer

        self.services = ServiceContainer.build_default()

    def initialize_database(self) -> None:
        """创建数据表，并在首次启动时尽力初始化最小演示数据。"""
        Base.metadata.create_all(bind=engine)

        with SessionLocal() as db:
            company_service = getattr(self.services, "company", None)
            if company_service is not None:
                bootstrap = getattr(company_service, "bootstrap_from_local_files", None)
                if callable(bootstrap):
                    try:
                        bootstrap(db)
                    except Exception:
                        pass

                backfill = getattr(
                    company_service,
                    "backfill_structured_tables_from_local_files",
                    None,
                )
                if callable(backfill):
                    try:
                        backfill(db)
                    except Exception:
                        pass

            self._ensure_demo_user(db)
            db.commit()

    def check_health(self) -> dict:
        """执行数据库连通性检查并返回关键表的记录数。"""
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
                counts = self._get_table_counts(db, self.TABLE_NAMES)
            return {"status": "ok", "tables": counts}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _ensure_demo_user(self, db) -> None:
        """
        保证至少存在一个演示用户。
        如果 users 表为空，则插入一个 demo 用户。
        """
        from sqlalchemy import select
        from app.core.database.models.user import User

        existing = db.execute(select(User).limit(1)).scalars().first()
        if existing is not None:
            return

        demo_user = User(
            username="demo_user",
            password_hash="demo_password_hash",
            role="user",
            status="active",
        )
        db.add(demo_user)
        db.flush()

    def _get_table_counts(self, db, table_names: list[str]) -> dict[str, int | str]:
        """
        获取表记录数。
        表不存在时返回 'missing'，避免健康检查直接失败。
        """
        counts: dict[str, int | str] = {}
        for table_name in table_names:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                counts[table_name] = int(result or 0)
            except Exception:
                counts[table_name] = "missing"
        return counts


def init_database() -> None:
    """调用数据库服务执行建表和初始化数据导入。"""
    DatabaseService().initialize_database()


def check_db_health() -> dict:
    """调用数据库服务返回数据库健康状态。"""
    return DatabaseService().check_health()