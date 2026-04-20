from __future__ import annotations

from core.repositories import AnnouncementRepository

from .base import BaseService
from .guards import require_positive_int, require_stock_code
from .requests import StockCodeDaysRequest, StockCodeRequest
from .serializers import model_to_dict


class AnnouncementService(BaseService):
    def __init__(self, *, ctx, company_service=None) -> None:
        super().__init__(ctx=ctx)
        self.company_service = company_service

    def get_raw_announcements(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_raw_announcements(db, req)), trace_id=req.trace_id)

    def get_structured_announcements(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_structured_announcements(db, req)), trace_id=req.trace_id)

    def get_drug_approvals(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_drug_approvals(db, req)), trace_id=req.trace_id)

    def get_clinical_trials(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_clinical_trials(db, req)), trace_id=req.trace_id)

    def get_procurement_events(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_procurement_events(db, req)), trace_id=req.trace_id)

    def get_regulatory_risks(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_regulatory_risks(db, req)), trace_id=req.trace_id)

    def get_company_event_summary(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_company_event_summary(db, req)), trace_id=req.trace_id)

    def _ensure_company(self, stock_code: str) -> None:
        if self.company_service:
            ok = self.company_service.ensure_company_exists(stock_code).data
            if not ok:
                raise ValueError(f"company not found: {stock_code}")

    def _get_raw_announcements(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_raw_announcements(stock_code, days=days)
        fields = ["id", "stock_code", "title", "publish_date", "announcement_type", "exchange", "content", "source_url", "source_type", "file_hash", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_structured_announcements(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_structured_announcements(stock_code, category=req.category, days=days)
        fields = ["id", "announcement_id", "stock_code", "category", "summary_text", "key_fields_json", "signal_type", "risk_level", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_drug_approvals(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_drug_approvals(stock_code, days=days)
        fields = ["id", "stock_code", "drug_name", "approval_type", "approval_date", "indication", "drug_stage", "is_innovative_drug", "review_status", "market_scope", "source_announcement_id", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_clinical_trials(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_clinical_trials(stock_code, days=days)
        fields = ["id", "stock_code", "drug_name", "trial_phase", "event_type", "event_date", "indication", "summary_text", "source_announcement_id", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_procurement_events(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_procurement_events(stock_code, days=days)
        fields = ["id", "stock_code", "drug_name", "procurement_round", "bid_result", "price_change_ratio", "event_date", "impact_summary", "source_announcement_id", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_regulatory_risks(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = AnnouncementRepository(db).list_regulatory_risks(stock_code, days=days)
        fields = ["id", "stock_code", "risk_type", "event_date", "risk_level", "summary_text", "source_announcement_id", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_company_event_summary(self, db, req: StockCodeDaysRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        structured = self._get_structured_announcements(db, req)
        approvals = self._get_drug_approvals(db, req)
        trials = self._get_clinical_trials(db, req)
        procurement = self._get_procurement_events(db, req)
        risks = self._get_regulatory_risks(db, req)
        opportunity_items = [x for x in structured if x.get("signal_type") == "opportunity"]
        risk_items = [x for x in structured if x.get("signal_type") == "risk"] + risks
        neutral_items = [x for x in structured if x.get("signal_type") in (None, "neutral", "")]
        counts_by_category: dict[str, int] = {}
        for item in structured:
            cat = item.get("category") or "unknown"
            counts_by_category[cat] = counts_by_category.get(cat, 0) + 1
        return {
            "stock_code": stock_code,
            "days": days,
            "structured_announcements": structured,
            "drug_approvals": approvals,
            "clinical_trials": trials,
            "procurement_events": procurement,
            "regulatory_risks": risks,
            "opportunity_items": opportunity_items,
            "risk_items": risk_items,
            "neutral_items": neutral_items,
            "counts_by_category": counts_by_category,
        }
