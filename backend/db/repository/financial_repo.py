"""财务指标仓储。"""

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from db.models.financial_data import FinancialData


class FinancialDataRepository:
    """负责标准化财务指标表的增量写入和查询。"""

    def upsert(
        self,
        db: Session,
        stock_code: str,
        stock_name: str,
        year: int,
        metric_name: str,
        metric_value: float | None,
        metric_unit: str | None = None,
        source: str | None = None,
        commit: bool = True,
    ) -> FinancialData:
        """插入或更新单条财务指标"""
        stmt = select(FinancialData).where(
            FinancialData.stock_code == stock_code,
            FinancialData.year == year,
            FinancialData.metric_name == metric_name,
        )
        existing = db.scalar(stmt)

        if existing:
            existing.metric_value = metric_value
            existing.metric_unit = metric_unit
            existing.source = source
            existing.stock_name = stock_name
            if commit:
                db.commit()
                db.refresh(existing)
            else:
                db.flush()
            return existing

        row = FinancialData(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            source=source,
        )
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def batch_upsert(self, db: Session, records: list[dict], commit: bool = True) -> int:
        """批量插入财务数据"""
        count = 0
        for record in records:
            self.upsert(
                db,
                stock_code=record["stock_code"],
                stock_name=record["stock_name"],
                year=record["year"],
                metric_name=record["metric_name"],
                metric_value=record.get("metric_value"),
                metric_unit=record.get("metric_unit"),
                source=record.get("source"),
                commit=False,
            )
            count += 1
        if commit and count:
            db.commit()
        return count

    def get_by_company_year(
        self, db: Session, stock_code: str, year: int
    ) -> list[FinancialData]:
        """查询某公司某年的所有指标"""
        stmt = (
            select(FinancialData)
            .where(FinancialData.stock_code == stock_code, FinancialData.year == year)
            .order_by(FinancialData.metric_name)
        )
        return list(db.scalars(stmt))

    def get_metric(
        self, db: Session, stock_code: str, year: int, metric_name: str
    ) -> FinancialData | None:
        """查询单个指标"""
        stmt = select(FinancialData).where(
            FinancialData.stock_code == stock_code,
            FinancialData.year == year,
            FinancialData.metric_name == metric_name,
        )
        return db.scalar(stmt)

    def compare_metric(
        self, db: Session, metric_name: str, year: int, stock_codes: list[str] | None = None
    ) -> list[FinancialData]:
        """横向对比多家公司的同一指标"""
        stmt = select(FinancialData).where(
            FinancialData.metric_name == metric_name,
            FinancialData.year == year,
        )
        if stock_codes:
            stmt = stmt.where(FinancialData.stock_code.in_(stock_codes))
        stmt = stmt.order_by(FinancialData.metric_value.desc())
        return list(db.scalars(stmt))

    def get_company_years(self, db: Session, stock_code: str) -> list[int]:
        """获取某公司有数据的年份列表"""
        stmt = (
            select(FinancialData.year)
            .where(FinancialData.stock_code == stock_code)
            .distinct()
            .order_by(FinancialData.year.desc())
        )
        return list(db.scalars(stmt))
