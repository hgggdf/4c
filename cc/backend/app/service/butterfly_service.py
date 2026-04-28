"""蝴蝶效应分析服务层。

从数据库拉取公司和财务数据，调用 ButterflyAnalyzer 流式输出，
流结束后把完整分析结果写入 NewsHot.key_fields_json 存档。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generator

from sqlalchemy import select, func

from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.news_hot import NewsHot
from app.core.repositories.news_repository import NewsRepository
from app.core.repositories.news_write_repository import NewsWriteRepository
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
            on_result=self._save_result,
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

    # ── 写库回调 ──────────────────────────────────────────────────────────

    def _save_result(self, result: dict) -> None:
        """把完整分析结果写入 NewsHot.key_fields_json。"""
        event_text = result.get("event_text", "")
        parsed = result.get("event_parsed", {})
        now = datetime.now()

        # news_uid 用事件文本 + 分析时间戳的 hash，保证每次分析独立存档
        uid_src = f"butterfly:{event_text}:{now.strftime('%Y%m%d%H%M%S')}"
        news_uid = hashlib.md5(uid_src.encode()).hexdigest()

        item = {
            "news_uid": news_uid,
            "title": f"【蝴蝶效应分析】{event_text[:60]}",
            "publish_time": now,
            "source_name": "butterfly_analyzer",
            "news_type": "butterfly_analysis",
            "content": result.get("narrative", ""),
            "summary_text": parsed.get("event_summary", event_text[:120]),
            "key_fields_json": {
                "event_text": event_text,
                "event_parsed": parsed,
                "industry_impacts": result.get("industry_impacts", []),
                "risk_alerts": result.get("risk_alerts", []),
                "opportunity_alerts": result.get("opportunity_alerts", []),
                "analyzed_at": now.isoformat(),
            },
        }

        try:
            self._with_db(lambda db: NewsWriteRepository(db).batch_upsert_news_raw([item]))
            logger.info("Butterfly analysis saved: %s", news_uid)
        except Exception as exc:
            logger.warning("Failed to save butterfly analysis: %s", exc)

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


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


__all__ = ["ButterflyService", "ButterflyRequest"]
