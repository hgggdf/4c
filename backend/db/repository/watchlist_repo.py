"""用户自选股仓储。"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data.pharma_company_registry import list_pharma_companies
from db.models.watchlist import Watchlist

DEFAULT_WATCHLIST = [
    {"stock_code": item["symbol"], "stock_name": item["name"]}
    for item in list_pharma_companies()
]


class WatchlistRepository:
    """负责自选股列表的读取、默认初始化、添加和删除。"""

    def list_by_user(self, db: Session, user_id: int) -> list[Watchlist]:
        """返回某个用户的全部自选股。"""
        stmt = select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.id.asc())
        return list(db.scalars(stmt))

    def seed_default(self, db: Session, user_id: int) -> list[Watchlist]:
        """为首次使用的用户灌入默认医药观察池。"""
        if self.list_by_user(db, user_id):
            return self.list_by_user(db, user_id)

        rows = [Watchlist(user_id=user_id, **item) for item in DEFAULT_WATCHLIST]
        db.add_all(rows)
        db.commit()
        return self.list_by_user(db, user_id)

    def add(self, db: Session, user_id: int, stock_code: str, stock_name: str | None) -> Watchlist:
        """向自选股列表中添加股票，若已存在则直接返回旧记录。"""
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.stock_code == stock_code,
        )
        existing = db.scalar(stmt)
        if existing:
            return existing

        row = Watchlist(user_id=user_id, stock_code=stock_code, stock_name=stock_name)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def remove(self, db: Session, user_id: int, stock_code: str) -> int:
        """从自选股列表中删除股票，并返回删除条数。"""
        stmt = delete(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.stock_code == stock_code,
        )
        result = db.execute(stmt)
        db.commit()
        return int(result.rowcount or 0)
