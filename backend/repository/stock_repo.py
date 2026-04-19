from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.stock_daily import StockDaily


class StockDailyRepository:
    def list_recent(self, db: Session, stock_code: str, days: int) -> list[StockDaily]:
        stmt = (
            select(StockDaily)
            .where(StockDaily.stock_code == stock_code)
            .order_by(StockDaily.trade_date.desc())
            .limit(days)
        )
        rows = list(db.scalars(stmt))
        rows.reverse()
        return rows

    def upsert_many(self, db: Session, stock_code: str, items: list[dict]) -> None:
        if not items:
            return

        existing_stmt = select(StockDaily).where(StockDaily.stock_code == stock_code)
        existing_rows = {row.trade_date: row for row in db.scalars(existing_stmt)}

        for item in items:
            trade_date = item["date"]
            if isinstance(trade_date, str):
                parsed_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
            elif isinstance(trade_date, datetime):
                parsed_date = trade_date.date()
            elif isinstance(trade_date, date):
                parsed_date = trade_date
            else:
                continue

            row = existing_rows.get(parsed_date)
            if row is None:
                row = StockDaily(
                    stock_code=stock_code,
                    trade_date=parsed_date,
                    open=item["open"],
                    close=item["close"],
                    high=item["high"],
                    low=item["low"],
                    volume=int(float(item["volume"])),
                )
                db.add(row)
                continue

            row.open = item["open"]
            row.close = item["close"]
            row.high = item["high"]
            row.low = item["low"]
            row.volume = int(float(item["volume"]))

        db.commit()
