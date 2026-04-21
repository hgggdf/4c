from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.macro_hot import MacroIndicatorHot
from app.core.repositories.base import BaseRepository


class MacroRepository(BaseRepository):
    def get_indicator(self, indicator_name: str, *, period: str | None = None) -> MacroIndicatorHot | None:
        stmt = select(MacroIndicatorHot).where(MacroIndicatorHot.indicator_name == indicator_name)
        if period is not None:
            stmt = stmt.where(MacroIndicatorHot.period == period)
        stmt = stmt.order_by(MacroIndicatorHot.period.desc(), MacroIndicatorHot.created_at.desc())
        return self.scalar_first(stmt)

    def list_indicators(self, indicator_names: list[str], *, periods: list[str] | None = None) -> list[MacroIndicatorHot]:
        stmt = select(MacroIndicatorHot).where(MacroIndicatorHot.indicator_name.in_(indicator_names))
        if periods:
            stmt = stmt.where(MacroIndicatorHot.period.in_(periods))
        stmt = stmt.order_by(MacroIndicatorHot.indicator_name.asc(), MacroIndicatorHot.period.desc())
        return self.scalars_all(stmt)

    def list_recent(self, indicator_names: list[str], *, recent_n: int = 6) -> list[MacroIndicatorHot]:
        stmt = select(MacroIndicatorHot).where(MacroIndicatorHot.indicator_name.in_(indicator_names))
        stmt = stmt.order_by(MacroIndicatorHot.indicator_name.asc(), MacroIndicatorHot.period.desc())
        return self.scalars_all(stmt)
