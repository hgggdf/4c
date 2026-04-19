from sqlalchemy.orm import Session
from sqlalchemy import text

from database.base import Base
from database.session import engine
from data.company_data_store import CompanyDataStore
from repository.user_repo import UserRepository
from repository.watchlist_repo import WatchlistRepository
import models  # noqa: F401


def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    user_repo = UserRepository()
    watchlist_repo = WatchlistRepository()
    company_store = CompanyDataStore()

    company_store.bootstrap_from_local_files()

    with Session(engine) as db:
        user = user_repo.get_or_create_demo_user(db)
        if not watchlist_repo.list_by_user(db, user.id):
            watchlist_repo.seed_default(db, user.id)


def check_db_health() -> dict:
    """检查数据库连接和各表数据量"""
    try:
        with Session(engine) as db:
            result = db.execute(text("SELECT 1")).scalar()
            counts = {}
            for table in [
                "users",
                "chat_history",
                "watchlist",
                "stock_daily",
                "financial_data",
                "macro_indicator",
                "company_dataset",
            ]:
                counts[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        return {"status": "ok", "tables": counts}
    except Exception as e:
        return {"status": "error", "message": str(e)}
