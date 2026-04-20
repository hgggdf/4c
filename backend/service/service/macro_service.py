from __future__ import annotations

from collections import defaultdict

from core.repositories import MacroRepository

from .base import BaseService
from .guards import require_non_empty, require_positive_int
from .requests import MacroIndicatorRequest, MacroListRequest, MacroSummaryRequest
from .serializers import model_to_dict


class MacroService(BaseService):
    def get_macro_indicator(self, req: MacroIndicatorRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_macro_indicator(db, req)), trace_id=req.trace_id)

    def list_macro_indicators(self, req: MacroListRequest):
        return self._run(lambda: self._with_db(lambda db: self._list_macro_indicators(db, req)), trace_id=req.trace_id)

    def get_macro_summary(self, req: MacroSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_macro_summary(db, req)), trace_id=req.trace_id)

    def _get_macro_indicator(self, db, req: MacroIndicatorRequest) -> dict | None:
        indicator_name = require_non_empty(req.indicator_name, "indicator_name")
        row = MacroRepository(db).get_indicator(indicator_name, period=req.period)
        if row is None:
            return None
        return model_to_dict(row, ["indicator_name", "period", "value", "unit", "source_type", "source_url", "created_at"])

    def _list_macro_indicators(self, db, req: MacroListRequest) -> list[dict]:
        if not req.indicator_names:
            raise ValueError("indicator_names is required")
        rows = MacroRepository(db).list_indicators(req.indicator_names, periods=req.periods)
        return [model_to_dict(r, ["indicator_name", "period", "value", "unit", "source_type", "source_url", "created_at"]) for r in rows]

    def _get_macro_summary(self, db, req: MacroSummaryRequest) -> dict:
        if not req.indicator_names:
            raise ValueError("indicator_names is required")
        recent_n = require_positive_int(req.recent_n, "recent_n")
        rows = MacroRepository(db).list_recent(req.indicator_names, recent_n=recent_n)
        grouped = defaultdict(list)
        for row in rows:
            grouped[row.indicator_name].append(model_to_dict(row, ["indicator_name", "period", "value", "unit", "source_type", "source_url", "created_at"]))
        for key in list(grouped.keys()):
            grouped[key] = grouped[key][:recent_n]
        return {"recent_n": recent_n, "series": dict(grouped)}
