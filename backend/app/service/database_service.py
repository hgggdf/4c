"""数据库初始化与健康检查服务。"""

from db.repository.db_stats_repo import DatabaseStatsRepository
from db.repository.user_repo import UserRepository
from db.repository.watchlist_repo import WatchlistRepository
from app.service.company_service import CompanyService
from db.base import Base
from db.session import SessionLocal, engine
import db.models as models  # noqa: F401


class DatabaseService:
    """封装建表、演示数据初始化和健康检查逻辑。"""

    TABLE_NAMES = [
        "users",
        "chat_history",
        "watchlist",
        "stock_daily",
        "financial_data",
        "macro_indicator",
        "company_dataset",
        "income_statement",
        "balance_sheet",
        "cashflow_statement",
        "financial_notes",
        "announcement_raw",
        "announcement_structured",
        "drug_approval",
        "capacity_expansion",
    ]

    def __init__(self) -> None:
        self.stats_repo = DatabaseStatsRepository()
        self.user_repo = UserRepository()
        self.watchlist_repo = WatchlistRepository()
        self.company_service = CompanyService()

    def initialize_database(self) -> None:
        """创建数据表，并在首次启动时导入本地数据和默认演示用户。"""
        Base.metadata.create_all(bind=engine)

        with SessionLocal() as db:
            self.company_service.bootstrap_from_local_files(db)
            self.company_service.backfill_structured_tables_from_local_files(db)

            user = self.user_repo.get_or_create_demo_user(db)
            if not self.watchlist_repo.list_by_user(db, user.id):
                self.watchlist_repo.seed_default(db, user.id)

    def check_health(self) -> dict:
        """执行数据库连通性检查并返回关键表的记录数。"""
        try:
            with SessionLocal() as db:
                self.stats_repo.ping(db)
                counts = self.stats_repo.get_table_counts(db, self.TABLE_NAMES)
            return {"status": "ok", "tables": counts}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}