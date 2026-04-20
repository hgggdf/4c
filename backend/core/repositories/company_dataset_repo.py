"""公司聚合资料仓储。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database.models.company_dataset import CompanyDataset


class CompanyDatasetRepository:
    """负责 company_dataset 表的统计、查询和写入。"""

    def count(self, db: Session) -> int:
        """统计公司聚合资料表中的记录数。"""
        stmt = select(func.count()).select_from(CompanyDataset)
        return db.scalar(stmt) or 0

    def get_by_symbol(self, db: Session, symbol: str) -> CompanyDataset | None:
        """按股票代码读取公司聚合资料。"""
        stmt = select(CompanyDataset).where(CompanyDataset.symbol == symbol)
        return db.scalar(stmt)

    def list_symbols(self, db: Session) -> list[str]:
        """列出已缓存公司资料的全部股票代码。"""
        stmt = select(CompanyDataset.symbol)
        return list(db.scalars(stmt))

    def list_summaries(self, db: Session) -> list[dict]:
        """读取数据库中的公司摘要信息。"""
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
        commit: bool = True,
    ) -> CompanyDataset:
        """插入或更新单家公司的聚合资料。"""
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

        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row