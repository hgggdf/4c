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
}


def _expand_names(names: list[str]) -> list[str]:
    """展开宏观指标名称别名，兼容中文展示名和英文简称。"""
    expanded = set(names)
    for name in names:
        for alias in _MACRO_NAME_ALIASES.get(name, []):
            expanded.add(alias)
    return list(expanded)


class MacroRepository(BaseRepository):
    """宏观指标读库入口。"""

    def get_indicator(self, indicator_name: str, *, period: str | None = None) -> MacroIndicator | None:
        """查询单个指标；未指定 period 时返回最新一期。"""
        names = _expand_names([indicator_name])
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name.in_(names))
        if period is not None:
            stmt = stmt.where(MacroIndicator.period == period)
        return self.scalar_first(stmt.order_by(MacroIndicator.period.desc()))

    def list_indicators(self, indicator_names: list[str], *, periods: list[str] | None = None) -> list[MacroIndicator]:
        """按指标名列表和可选期间列表查询宏观指标。"""
        names = _expand_names(indicator_names)
        stmt = select(MacroIndicator).where(MacroIndicator.indicator_name.in_(names))
        if periods:
            stmt = stmt.where(MacroIndicator.period.in_(periods))
        return self.scalars_all(stmt.order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc()))

    def list_recent(self, indicator_names: list[str], *, recent_n: int = 6) -> list[MacroIndicator]:
        """查询最近指标记录。

        recent_n 当前未在 SQL 层截断，调用方如果需要每个指标 N 条需自行处理。
        """
        names = _expand_names(indicator_names)
        return self.scalars_all(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_name.in_(names))
            .order_by(MacroIndicator.indicator_name.asc(), MacroIndicator.period.desc())
        )
