"""蝴蝶效应分析服务层。

从数据库拉取公司和财务数据，调用 ButterflyAnalyzer 流式输出。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Generator

from sqlalchemy import select, func

from app.core.utils.convert import to_float as _to_float
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.news_hot import NewsHot
from app.core.repositories.news_repository import NewsRepository
from .base import BaseService
from .dto import BaseRequest
from .serializers import model_to_dict

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ButterflyRequest(BaseRequest):
    event: str = ""
    industry_filter: list[str] = field(default_factory=list)
    max_companies: int = 30


@dataclass(slots=True)
class ButterflyHistoryRequest(BaseRequest):
    days: int = 90
    event_type: str | None = None
    severity: str | None = None
    keyword: str | None = None
    limit: int = 50


class ButterflyService(BaseService):

    def analyze_stream(self, req: ButterflyRequest) -> Generator[dict, None, None]:
        if not req.event.strip():
            yield {"type": "error", "message": "事件描述不能为空"}
            return

        try:
            company_exposures = self._with_db(
                lambda db: self._load_company_exposures(db, req)
            )
        except Exception as exc:
            logger.warning("Failed to load company exposures: %s", exc)
            company_exposures = []

        from agent.butterfly_analyzer import ButterflyAnalyzer
        analyzer = ButterflyAnalyzer()

        yield from analyzer.analyze_stream(
            req.event,
            company_exposures=company_exposures,
        )

    def list_history(self, req: ButterflyHistoryRequest):
        """查询历史蝴蝶效应分析记录。"""
        return self._run(
            lambda: self._with_db(lambda db: self._list_history(db, req)),
            trace_id=req.trace_id,
        )

    def _list_history(self, db, req: ButterflyHistoryRequest) -> list[dict]:
        rows = NewsRepository(db).list_butterfly_analyses(
            days=req.days,
            event_type=req.event_type,
            severity=req.severity,
            keyword=req.keyword,
            limit=req.limit,
        )
        results = []
        for r in rows:
            kf = r.key_fields_json or {}
            ep = kf.get("event_parsed", {})
            results.append({
                "id": r.id,
                "news_uid": r.news_uid,
                "title": r.title,
                "event_text": kf.get("event_text", ""),
                "event_type": ep.get("event_type"),
                "severity": ep.get("severity"),
                "time_horizon": ep.get("time_horizon"),
                "primary_shocks": ep.get("primary_shocks", []),
                "industry_impacts": kf.get("industry_impacts", []),
                "risk_alerts": kf.get("risk_alerts", []),
                "opportunity_alerts": kf.get("opportunity_alerts", []),
                "analyzed_at": kf.get("analyzed_at"),
                "narrative": r.content or "",
            })
        return results

    # ── 数据库查询 ────────────────────────────────────────────────────────

    def _load_company_exposures(self, db, req: ButterflyRequest) -> list[dict]:
        stmt = select(Company)
        if req.industry_filter:
            stmt = stmt.where(Company.industry_level2.in_(req.industry_filter))
        companies = db.execute(stmt).scalars().all()
        if not companies:
            return []

        stock_codes = [c.stock_code for c in companies]
        company_map = {c.stock_code: c for c in companies}

        subq = (
            select(
                FinancialHot.stock_code,
                func.max(FinancialHot.report_date).label("max_date"),
            )
            .where(FinancialHot.stock_code.in_(stock_codes))
            .group_by(FinancialHot.stock_code)
            .subquery()
        )
        fin_rows = db.execute(
            select(FinancialHot).join(
                subq,
                (FinancialHot.stock_code == subq.c.stock_code)
                & (FinancialHot.report_date == subq.c.max_date),
            )
        ).scalars().all()
        fin_map: dict[str, FinancialHot] = {r.stock_code: r for r in fin_rows}

        results = []
        for code, comp in company_map.items():
            fin = fin_map.get(code)
            entry: dict[str, Any] = {
                "stock_code": code,
                "stock_name": comp.stock_name,
                "industry_level2": comp.industry_level2 or "",
            }
            if fin:
                entry["gross_margin"] = _to_float(fin.gross_margin)
                entry["rd_ratio"] = _to_float(fin.rd_ratio)
                entry["debt_ratio"] = _to_float(fin.debt_ratio)
                rev = _to_float(fin.revenue)
                cost = _to_float(fin.operating_cost)
                if rev and rev > 0 and cost is not None:
                    entry["operating_cost_ratio"] = cost / rev
            results.append(entry)

        return results[:req.max_companies]

__all__ = ["ButterflyService", "ButterflyRequest"]
