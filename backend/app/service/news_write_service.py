from __future__ import annotations

from app.core.repositories.news_write_repository import NewsWriteRepository

from .base import BaseService
from .guards import require_positive_int, require_stock_code
from .write_requests import BatchItemsRequest, ReplaceNewsCompanyMapRequest, ReplaceNewsIndustryMapRequest


class NewsWriteService(BaseService):
    def batch_upsert_news_raw(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "raw")), trace_id=req.trace_id)

    def batch_upsert_news_structured(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "structured")), trace_id=req.trace_id)

    def replace_news_industry_map(self, req: ReplaceNewsIndustryMapRequest):
        return self._run(lambda: self._with_db(lambda db: self._replace_news_industry_map(db, req)), trace_id=req.trace_id)

    def replace_news_company_map(self, req: ReplaceNewsCompanyMapRequest):
        return self._run(lambda: self._with_db(lambda db: self._replace_news_company_map(db, req)), trace_id=req.trace_id)

    def batch_upsert_industry_impact_events(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "impact")), trace_id=req.trace_id)

    def _batch_upsert(self, db, req: BatchItemsRequest, mode: str) -> dict:
        if not req.items:
            raise ValueError("items is required")
        repo = NewsWriteRepository(db)
        sync_status = None
        if mode == "raw":
            entities, created, updated = repo.batch_upsert_news_raw(req.items)
            if req.sync_vector_index:
                sync_status = self._sync_news(db, [e.id for e in entities])
        elif mode == "structured":
            entities, created, updated = repo.batch_upsert_news_structured(req.items)
        elif mode == "impact":
            entities, created, updated = repo.batch_upsert_industry_impact_events(req.items)
        else:
            raise ValueError(f"unsupported mode: {mode}")
        result = {
            "created_count": created,
            "updated_count": updated,
            "total": len(entities),
            "ids": [e.id for e in entities],
        }
        if sync_status is not None:
            result["sync_status"] = sync_status
        return result

    def _replace_news_industry_map(self, db, req: ReplaceNewsIndustryMapRequest) -> dict:
        news_id = require_positive_int(req.news_id, "news_id")
        items = []
        for item in req.items:
            payload = dict(item)
            payload["impact_direction"] = payload.get("impact_direction")
            items.append(payload)
        entities = NewsWriteRepository(db).replace_news_industry_map(news_id, items)
        return {"news_id": news_id, "mapping_count": len(entities), "industry_codes": [e.industry_code for e in entities]}

    def _replace_news_company_map(self, db, req: ReplaceNewsCompanyMapRequest) -> dict:
        news_id = require_positive_int(req.news_id, "news_id")
        items = []
        for item in req.items:
            payload = dict(item)
            if payload.get("stock_code"):
                payload["stock_code"] = require_stock_code(payload["stock_code"])
            items.append(payload)
        entities = NewsWriteRepository(db).replace_news_company_map(news_id, items)
        return {"news_id": news_id, "mapping_count": len(entities), "stock_codes": [e.stock_code for e in entities]}

    def _sync_news(self, db, source_ids: list[int]) -> str:
        try:
            from app.knowledge import sync as kg_sync
            kg_sync.sync_news_by_ids(db, source_ids, is_hot=True)
            return "synced"
        except Exception:
            return "skipped"
