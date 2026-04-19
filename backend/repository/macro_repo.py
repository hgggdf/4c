from sqlalchemy import select
from sqlalchemy.orm import Session

from models.financial_data import MacroIndicator


class MacroIndicatorRepository:
    def upsert(
        self,
        db: Session,
        indicator_name: str,
        period: str,
        value: float | None,
        unit: str | None = None,
        source: str | None = None,
    ) -> MacroIndicator:
        stmt = select(MacroIndicator).where(
            MacroIndicator.indicator_name == indicator_name,
            MacroIndicator.period == period,
        )
        existing = db.scalar(stmt)

        if existing:
            existing.value = value
            existing.unit = unit
            existing.source = source
            db.commit()
            db.refresh(existing)
            return existing

        row = MacroIndicator(
            indicator_name=indicator_name,
            period=period,
            value=value,
            unit=unit,
            source=source,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def get_series(self, db: Session, indicator_name: str) -> list[MacroIndicator]:
        stmt = (
            select(MacroIndicator)
            .where(MacroIndicator.indicator_name == indicator_name)
            .order_by(MacroIndicator.period)
        )
        return list(db.scalars(stmt))

    def get_latest(self, db: Session, indicator_name: str) -> MacroIndicator | None:
        stmt = (
            select(MacroIndicator)
            .where(MacroIndicator.indicator_name == indicator_name)
            .order_by(MacroIndicator.period.desc())
            .limit(1)
        )
        return db.scalar(stmt)
