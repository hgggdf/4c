from sqlalchemy.orm import Session

from app.data.akshare_client import StockDataProvider
from db.repository.db_stats_repo import DatabaseStatsRepository
from db.repository.stock_repo import StockDailyRepository
from db.repository.user_repo import UserRepository
from db.repository.watchlist_repo import WatchlistRepository
from app.service.company_service import CompanyService


class StockService:
    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.company_service = CompanyService()
        self.stock_repo = StockDailyRepository()
        self.stats_repo = DatabaseStatsRepository()
        self.user_repo = UserRepository()
        self.watchlist_repo = WatchlistRepository()

    def get_quote(self, symbol: str):
        return self.provider.get_quote(symbol)

    def get_kline(self, db: Session, symbol: str, days: int = 30):
        cached = self.stock_repo.list_recent(db, symbol, days)
        if len(cached) >= days:
            return [
                {
                    "date": row.trade_date.strftime("%Y-%m-%d"),
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                }
                for row in cached
            ]

        fresh = self.provider.get_kline(symbol, days)
        self.stock_repo.upsert_many(db, symbol, fresh)
        return fresh

    def get_watchlist(self, db: Session, user_id: int):
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id

        rows = self.watchlist_repo.list_by_user(db, user_id)
        if not rows:
            rows = self.watchlist_repo.seed_default(db, user_id)
        return [{"symbol": row.stock_code, "name": row.stock_name or row.stock_code} for row in rows]

    def add_watchlist(self, db: Session, user_id: int, symbol: str, name: str | None):
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id
        row = self.watchlist_repo.add(db, user_id, symbol, name)
        return {"symbol": row.stock_code, "name": row.stock_name or row.stock_code}

    def remove_watchlist(self, db: Session, user_id: int, symbol: str):
        return {"removed": self.watchlist_repo.remove(db, user_id, symbol)}

    def list_pharma_companies(self, db: Session):
        return self.company_service.list_company_summaries(db)

    def get_company_dataset(self, db: Session, symbol: str, refresh: bool = False, compact: bool = True):
        return self.company_service.get_company_dataset(db, symbol, refresh=refresh, compact=compact)

    def refresh_all_company_data(self, db: Session, compact: bool = True):
        return self.company_service.refresh_all_company_data(db, compact=compact)

    def build_company_agent_context(self, db: Session, symbol: str) -> str:
        return self.company_service.build_company_agent_context(db, symbol)

    def get_db_stats(self, db: Session):
        rows = self.stats_repo.list_stock_daily_stats(db)
        return {"total_stocks": len(rows), "stocks": rows}
