from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.company_dataset import CompanyDataset


class CompanyDatasetRepository:
    def count(self, db: Session) -> int:
        stmt = select(func.count()).select_from(CompanyDataset)
        return db.scalar(stmt) or 0

    def get_by_symbol(self, db: Session, symbol: str) -> CompanyDataset | None:
        stmt = select(CompanyDataset).where(CompanyDataset.symbol == symbol)
        return db.scalar(stmt)

    def list_symbols(self, db: Session) -> list[str]:
        stmt = select(CompanyDataset.symbol)
        return list(db.scalars(stmt))

    def list_summaries(self, db: Session) -> list[dict]:
        stmt = select(CompanyDataset.symbol, CompanyDataset.summary_json).order_by(CompanyDataset.symbol)
        return [
            {"symbol": symbol, "summary_json": summary_json or {}}
            for symbol, summary_json in db.execute(stmt).all()
        ]

    def upsert(
        self,
        db: Session,
        *,
        symbol: str,
        name: str,
        exchange: str | None,
        collected_at: str | None,
        summary_json: dict,
        compact_json: dict,
        dataset_json: dict,
    ) -> CompanyDataset:
        row = self.get_by_symbol(db, symbol)
        if row is None:
            row = CompanyDataset(
                symbol=symbol,
                name=name,
                exchange=exchange,
                collected_at=collected_at,
                summary_json=summary_json,
                compact_json=compact_json,
                dataset_json=dataset_json,
            )
            db.add(row)
        else:
            row.name = name
            row.exchange = exchange
            row.collected_at = collected_at
            row.summary_json = summary_json
            row.compact_json = compact_json
            row.dataset_json = dataset_json

        db.commit()
        db.refresh(row)
        return row