"""股票业务服务，负责行情查询、自选股管理和公司资料读取。"""

from sqlalchemy.orm import Session

from external.akshare_client import StockDataProvider
from core.repositories.db_stats_repo import DatabaseStatsRepository
from core.repositories.stock_repo import StockDailyRepository
from core.repositories.user_repo import UserRepository
from core.repositories.watchlist_repo import WatchlistRepository
from modules.company.service import CompanyService


class StockService:
    """封装股票相关的核心业务逻辑，供 API 和 agent 复用。"""

    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.company_service = CompanyService()
        self.stock_repo = StockDailyRepository()
        self.stats_repo = DatabaseStatsRepository()
        self.user_repo = UserRepository()
        self.watchlist_repo = WatchlistRepository()

    def get_quote(self, symbol: str):
        """获取指定股票的最新行情。"""
        return self.provider.get_quote(symbol)

    def get_kline(self, db: Session, symbol: str, days: int = 30):
        """优先读取本地缓存的 K 线，不足时从外部源补拉并写回数据库。"""
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
        """读取用户自选股，必要时自动创建演示用户和默认观察池。"""
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id

        rows = self.watchlist_repo.list_by_user(db, user_id)
        if not rows:
            rows = self.watchlist_repo.seed_default(db, user_id)
        return [{"symbol": row.stock_code, "name": row.stock_name or row.stock_code} for row in rows]

    def add_watchlist(self, db: Session, user_id: int, symbol: str, name: str | None):
        """向用户自选股列表中新增标的。"""
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id
        row = self.watchlist_repo.add(db, user_id, symbol, name)
        return {"symbol": row.stock_code, "name": row.stock_name or row.stock_code}

    def remove_watchlist(self, db: Session, user_id: int, symbol: str):
        """从用户自选股列表中移除标的。"""
        return {"removed": self.watchlist_repo.remove(db, user_id, symbol)}

    def list_pharma_companies(self, db: Session):
        """返回医药公司观察池的概览信息。"""
        return self.company_service.list_company_summaries(db)

    def get_company_dataset(self, db: Session, symbol: str, refresh: bool = False, compact: bool = True):
        """获取单家公司的聚合资料。"""
        return self.company_service.get_company_dataset(db, symbol, refresh=refresh, compact=compact)

    def refresh_all_company_data(self, db: Session, compact: bool = True):
        """批量刷新全部观察池公司的聚合资料。"""
        return self.company_service.refresh_all_company_data(db, compact=compact)

    def build_company_agent_context(self, db: Session, symbol: str) -> str:
        """构造供智能体使用的公司上下文。"""
        return self.company_service.build_company_agent_context(db, symbol)

    def get_db_stats(self, db: Session):
        """读取股票历史行情缓存表的统计信息。"""
        rows = self.stats_repo.list_stock_daily_stats(db)
        return {"total_stocks": len(rows), "stocks": rows}
