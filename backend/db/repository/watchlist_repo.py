from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data.pharma_company_registry import list_pharma_companies
from db.models.watchlist import Watchlist

DEFAULT_WATCHLIST = [
    {"stock_code": item["symbol"], "stock_name": item["name"]}
    for item in list_pharma_companies()
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
