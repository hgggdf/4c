from __future__ import annotations

from collections import Counter

from app.core.repositories import NewsRepository

from .base import BaseService
from .guards import require_non_empty, require_positive_int, require_stock_code
from .requests import ImpactSummaryRequest, IndustryDaysRequest, NewsRawRequest, NewsStructuredRequest, SearchRequest, StockCodeDaysRequest, StockCodeRequest
from .serializers import model_to_dict


class NewsService(BaseService):
    def __init__(self, *, ctx, company_service=None, retrieval_service=None) -> None:
        super().__init__(ctx=ctx)
        self.company_service = company_service
        self.retrieval_service = retrieval_service

    def get_news_raw(self, req: NewsRawRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_news_raw(db, req)), trace_id=req.trace_id)

    def get_news_by_company(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_news_by_company(db, req)), trace_id=req.trace_id)

    def get_news_by_industry(self, req: IndustryDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_news_by_industry(db, req)), trace_id=req.trace_id)

    def get_news_structured(self, req: NewsStructuredRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_news_structured(db, req)), trace_id=req.trace_id)

    def get_company_news_impact(self, req: StockCodeDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_company_news_impact(db, req)), trace_id=req.trace_id)

    def get_industry_news_impact(self, req: IndustryDaysRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_industry_news_impact(db, req)), trace_id=req.trace_id)

    def get_news_impact_summary(self, req: ImpactSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_news_impact_summary(db, req)), trace_id=req.trace_id)

    def _ensure_company(self, stock_code: str) -> None:
        if self.company_service:
            ok = self.company_service.ensure_company_exists(stock_code).data
            if not ok:
                raise ValueError(f"company not found: {stock_code}")

    def _news_raw_dict(self, row) -> dict:
        return model_to_dict(row, ["id", "news_uid", "title", "publish_time", "source_name", "source_url", "author_name", "content", "news_type", "language", "file_hash", "created_at"])

    def _structured_dict(self, row) -> dict:
        return model_to_dict(row, ["id", "news_id", "topic_category", "summary_text", "keywords_json", "signal_type", "impact_level", "impact_horizon", "sentiment_label", "confidence_score", "created_at"])

    def _get_news_raw(self, db, req: NewsRawRequest) -> list[dict]:
        days = require_positive_int(req.days, "days")
        rows = NewsRepository(db).list_news_raw(days=days, news_type=req.news_type)
        return [self._news_raw_dict(r) for r in rows]

    def _get_news_by_company(self, db, req: StockCodeDaysRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        self._ensure_company(stock_code)
        rows = NewsRepository(db).list_news_by_company(stock_code, days=days)
        results = []
        for mapping, news in rows:
            item = self._news_raw_dict(news)
            item.update({
                "impact_direction": mapping.impact_direction,
                "impact_strength": float(mapping.impact_strength) if mapping.impact_strength is not None else None,
                "reason_text": mapping.reason_text,
            })
            results.append(item)
        return results

    def _get_news_by_industry(self, db, req: IndustryDaysRequest) -> list[dict]:
        industry_code = require_non_empty(req.industry_code, "industry_code")
        days = require_positive_int(req.days, "days")
        rows = NewsRepository(db).list_news_by_industry(industry_code, days=days)
        results = []
        for mapping, news in rows:
            item = self._news_raw_dict(news)
            item.update({
                "industry_code": mapping.industry_code,
                "impact_direction": mapping.impact_direction,
                "impact_strength": float(mapping.impact_strength) if mapping.impact_strength is not None else None,
                "reason_text": mapping.reason_text,
            })
            results.append(item)
        return results

    def _get_news_structured(self, db, req: NewsStructuredRequest) -> list[dict]:
        days = require_positive_int(req.days, "days")
        rows = NewsRepository(db).list_news_structured(days=days, topic_category=req.topic_category)
        return [self._structured_dict(r) for r in rows]

    def _get_company_news_impact(self, db, req: StockCodeDaysRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        days = require_positive_int(req.days, "days")
        items = self._get_news_by_company(db, req)
        directions = Counter(item.get("impact_direction") or "unknown" for item in items)
        avg_strength = None
        strengths = [item["impact_strength"] for item in items if item.get("impact_strength") is not None]
        if strengths:
            avg_strength = sum(strengths) / len(strengths)
        evidence = None
        if self.retrieval_service:
            evidence = self.retrieval_service.search_news_evidence(
                SearchRequest(query="新闻 影响 风险 机会", stock_code=stock_code, top_k=5, trace_id=req.trace_id)
            ).data
        return {
            "stock_code": stock_code,
            "days": days,
            "items": items,
            "direction_counts": dict(directions),
            "avg_impact_strength": avg_strength,
            "evidence": evidence,
        }

    def _get_industry_news_impact(self, db, req: IndustryDaysRequest) -> dict:
        industry_code = require_non_empty(req.industry_code, "industry_code")
        days = require_positive_int(req.days, "days")
        items = self._get_news_by_industry(db, req)
        events = [model_to_dict(r, ["id", "industry_code", "news_id", "event_type", "impact_direction", "impact_level", "impact_horizon", "summary_text", "event_date", "created_at"]) for r in NewsRepository(db).list_industry_impact_events(industry_code, days=days)]
        directions = Counter(item.get("impact_direction") or "unknown" for item in items)
        strengths = [item["impact_strength"] for item in items if item.get("impact_strength") is not None]
        avg_strength = (sum(strengths) / len(strengths)) if strengths else None
        evidence = None
        if self.retrieval_service:
            evidence = self.retrieval_service.search_news_evidence(
                SearchRequest(query="行业 新闻 影响", industry_code=industry_code, top_k=5, trace_id=req.trace_id)
            ).data
        return {
            "industry_code": industry_code,
            "days": days,
            "items": items,
            "impact_events": events,
            "direction_counts": dict(directions),
            "avg_impact_strength": avg_strength,
            "evidence": evidence,
        }

    def _get_news_impact_summary(self, db, req: ImpactSummaryRequest) -> dict:
        days = require_positive_int(req.days, "days")
        if req.stock_code:
            return self._get_company_news_impact(db, StockCodeDaysRequest(stock_code=req.stock_code, days=days, trace_id=req.trace_id))
        if req.industry_code:
            return self._get_industry_news_impact(db, IndustryDaysRequest(industry_code=req.industry_code, days=days, trace_id=req.trace_id))
        raw = self._get_news_raw(db, NewsRawRequest(days=days, trace_id=req.trace_id))
        structured = self._get_news_structured(db, NewsStructuredRequest(days=days, trace_id=req.trace_id))
        sentiments = Counter(item.get("sentiment_label") or "unknown" for item in structured)
        return {"days": days, "raw_items": raw, "structured_items": structured, "sentiment_counts": dict(sentiments)}
