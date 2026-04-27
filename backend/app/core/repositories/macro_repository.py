from __future__ import annotations

from app.core.database.models.macro_hot import MacroIndicator
from app.core.repositories.base import BaseRepository
from sqlalchemy import or_, select

_MACRO_NAME_ALIASES = {
    "GDP增速": ["GDP"],
    "GDP": ["GDP增速"],
    "CPI同比": ["CPI"],
    "CPI": ["CPI同比"],
    "PPI同比": ["PPI"],
    "PPI": ["PPI同比"],
    "社融存量同比": ["社融"],
    "社融": ["社融存量同比"],
    "医药研发投入增速": ["医药研发投入"],
    "医药研发投入": ["医药研发投入增速"],
}


def _expand_names(names: list[str]) -> list[str]:
    expanded = set(names)
    for name in names:
        for alias in _MACRO_NAME_ALIASES.get(name, []):
            expanded.add(alias)
    return list(expanded)


class MacroRepository(BaseRepository):
    def get_indicator(self, indicator_name: str, *, period: str | None = None) -> MacroIndicator | None:
        names = _expand_names([indicator_name])
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name.in_(names))
        if period is not None:
            stmt = stmt.where(MacroIndicator.period == period)
        return self.scalar_first(stmt.order_by(MacroIndicator.period.desc()))

    def list_indicators(self, indicator_names: list[str], *, periods: list[str] | None = None) -> list[MacroIndicator]:
        names = _expand_names(indicator_names)
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name.in_(names))
        if periods:
            stmt = stmt.where(MacroIndicator.period.in_(periods))
        return self.scalars_all(stmt.order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc()))

    def list_recent(self, indicator_names: list[str], *, recent_n: int = 6) -> list[MacroIndicator]:
        names = _expand_names(indicator_names)
        return self.scalars_all(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_name.in_(names))
            .order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc())
        )
