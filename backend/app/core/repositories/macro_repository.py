from __future__ import annotations

from app.core.database.models.macro_hot import MacroIndicator
from app.core.repositories.base import BaseRepository
from sqlalchemy import select


class MacroRepository(BaseRepository):
    def get_indicator(self, indicator_name: str, *, period: str | None = None) -> MacroIndicator | None:
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name == indicator_name)
        if period is not None:
            stmt = stmt.where(MacroIndicator.period == period)
        return self.scalar_first(stmt.order_by(MacroIndicator.period.desc()))

    def list_indicators(self, indicator_names: list[str], *, periods: list[str] | None = None) -> list[MacroIndicator]:
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name.in_(indicator_names))
        if periods:
            stmt = stmt.where(MacroIndicator.period.in_(periods))
        return self.scalars_all(stmt.order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc()))

    def list_recent(self, indicator_names: list[str], *, recent_n: int = 6) -> list[MacroIndicator]:
        return self.scalars_all(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_name.in_(indicator_names))
            .order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc())
        )
