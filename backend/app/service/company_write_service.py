from __future__ import annotations

from datetime import datetime

from app.core.repositories.company_write_repository import CompanyWriteRepository

from .base import BaseService
from .guards import require_positive_int, require_stock_code
from .serializers import model_to_dict
from .write_requests import (
    BatchUpsertIndustriesRequest,
    ReplaceCompanyIndustriesRequest,
    UpsertCompanyMasterRequest,
    UpsertCompanyProfileRequest,
    UpsertWatchlistRequest,
)


class CompanyWriteService(BaseService):
    def upsert_company_master(self, req: UpsertCompanyMasterRequest):
        return self._run(lambda: self._with_db(lambda db: self._upsert_company_master(db, req)), trace_id=req.trace_id)

    def batch_upsert_company_master(self, req: BatchUpsertIndustriesRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert_company_master(db, req)), trace_id=req.trace_id)

    def upsert_company_profile(self, req: UpsertCompanyProfileRequest):
        return self._run(lambda: self._with_db(lambda db: self._upsert_company_profile(db, req)), trace_id=req.trace_id)

    def batch_upsert_industries(self, req: BatchUpsertIndustriesRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert_industries(db, req)), trace_id=req.trace_id)

    def replace_company_industries(self, req: ReplaceCompanyIndustriesRequest):
        return self._run(lambda: self._with_db(lambda db: self._replace_company_industries(db, req)), trace_id=req.trace_id)

    def upsert_watchlist(self, req: UpsertWatchlistRequest):
        return self._run(lambda: self._with_db(lambda db: self._upsert_watchlist(db, req)), trace_id=req.trace_id)

    def _upsert_company_master(self, db, req: UpsertCompanyMasterRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        payload = {
            "stock_code": stock_code,
            "stock_name": (req.stock_name or "").strip(),
            "full_name": req.full_name,
            "exchange": req.exchange,
            "industry_level1": req.industry_level1,
            "industry_level2": req.industry_level2,
            "listing_date": req.listing_date,
            "status": req.status or "active",
            "alias_json": req.alias_json,
            "source_type": req.source_type,
            "source_url": req.source_url,
            "updated_at": datetime.now(),
        }
        entity, created = CompanyWriteRepository(db).upsert_company_master(payload)
        result = model_to_dict(entity, ["id", "stock_code", "stock_name", "full_name", "exchange", "industry_level1", "industry_level2", "listing_date", "status", "alias_json", "source_type", "source_url", "created_at", "updated_at"])
        result["created"] = created
        return result

    def _batch_upsert_company_master(self, db, req: BatchUpsertIndustriesRequest) -> dict:
        if not req.items:
            raise ValueError("items is required")
        items = []
        for item in req.items:
            stock_code = require_stock_code(item.get("stock_code"))
            payload = dict(item)
            payload["stock_code"] = stock_code
            payload.setdefault("status", "active")
            payload["updated_at"] = datetime.now()
            items.append(payload)
        entities, created, updated = CompanyWriteRepository(db).batch_upsert_company_master(items)
        return {
            "created_count": created,
            "updated_count": updated,
            "total": len(entities),
            "stock_codes": [e.stock_code for e in entities],
        }

    def _upsert_company_profile(self, db, req: UpsertCompanyProfileRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        payload = {
            "stock_code": stock_code,
            "business_summary": req.business_summary,
            "core_products_json": req.core_products_json,
            "main_segments_json": req.main_segments_json,
            "market_position": req.market_position,
            "management_summary": req.management_summary,
            "updated_at": datetime.now(),
        }
        repo = CompanyWriteRepository(db)
        entity, created = repo.upsert_company_profile(payload)
        sync_status = None
        if req.sync_vector_index:
            sync_status = self._sync_company_profile(db, [entity.id])
        result = model_to_dict(entity, ["id", "stock_code", "business_summary", "core_products_json", "main_segments_json", "market_position", "management_summary", "updated_at"])
        result["created"] = created
        result["sync_status"] = sync_status
        return result

    def _sync_company_profile(self, db, source_ids: list[int]) -> str:
        try:
            from app.knowledge import sync as kg_sync
            kg_sync.sync_company_profiles_by_ids(db, source_ids)
            return "synced"
        except Exception:
            return "skipped"

    def _batch_upsert_industries(self, db, req: BatchUpsertIndustriesRequest) -> dict:
        if not req.items:
            raise ValueError("items is required")
        entities, created, updated = CompanyWriteRepository(db).batch_upsert_industries(req.items)
        return {
            "created_count": created,
            "updated_count": updated,
            "total": len(entities),
            "industry_codes": [e.industry_code for e in entities],
        }

    def _replace_company_industries(self, db, req: ReplaceCompanyIndustriesRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        items = []
        for item in req.items:
            items.append({
                "industry_code": item["industry_code"],
                "is_primary": int(item.get("is_primary", 0)),
                "created_at": item.get("created_at") or datetime.now(),
            })
        entities = CompanyWriteRepository(db).replace_company_industries(stock_code, items)
        return {
            "stock_code": stock_code,
            "mapping_count": len(entities),
            "industry_codes": [e.industry_code for e in entities],
        }

    def _upsert_watchlist(self, db, req: UpsertWatchlistRequest) -> dict:
        user_id = require_positive_int(req.user_id, "user_id")
        stock_code = require_stock_code(req.stock_code)
        entity, created = CompanyWriteRepository(db).upsert_watchlist(
            {
                "user_id": user_id,
                "stock_code": stock_code,
                "remark": req.remark,
                "tags_json": req.tags_json,
                "alert_enabled": int(req.alert_enabled),
            }
        )
        result = model_to_dict(entity, ["id", "user_id", "stock_code", "remark", "tags_json", "alert_enabled", "created_at"])
        result["created"] = created
        return result
