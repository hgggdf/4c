from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.watchlist import Watchlist

DEFAULT_WATCHLIST = [
    {"stock_code": "600519", "stock_name": "贵州茅台"},
    {"stock_code": "000001", "stock_name": "平安银行"},
    {"stock_code": "600036", "stock_name": "招商银行"},
    {"stock_code": "300750", "stock_name": "宁德时代"},
    {"stock_code": "002594", "stock_name": "比亚迪"},
]


class WatchlistRepository:
    def list_by_user(self, db: Session, user_id: int) -> list[Watchlist]:
        stmt = select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.id.asc())
        return list(db.scalars(stmt))

    def seed_default(self, db: Session, user_id: int) -> list[Watchlist]:
        if self.list_by_user(db, user_id):
            return self.list_by_user(db, user_id)

        rows = [Watchlist(user_id=user_id, **item) for item in DEFAULT_WATCHLIST]
        db.add_all(rows)
        db.commit()
        return self.list_by_user(db, user_id)

    def add(self, db: Session, user_id: int, stock_code: str, stock_name: str | None) -> Watchlist:
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
        stmt = delete(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.stock_code == stock_code,
        )
        result = db.execute(stmt)
        db.commit()
        return int(result.rowcount or 0)
