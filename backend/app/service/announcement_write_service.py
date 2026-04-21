from __future__ import annotations

from app.core.repositories.announcement_write_repository import AnnouncementWriteRepository

from .base import BaseService
from .guards import require_stock_code
from .write_requests import BatchItemsRequest


class AnnouncementWriteService(BaseService):
    def batch_upsert_raw_announcements(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "raw")), trace_id=req.trace_id)

    def batch_delete_raw_announcements(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "raw")), trace_id=req.trace_id)

    def batch_upsert_structured_announcements(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "structured")), trace_id=req.trace_id)

    def batch_delete_structured_announcements(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "structured")), trace_id=req.trace_id)

    def batch_upsert_drug_approvals(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "approvals")), trace_id=req.trace_id)

    def batch_delete_drug_approvals(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "approvals")), trace_id=req.trace_id)

    def batch_upsert_clinical_trials(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "trials")), trace_id=req.trace_id)

    def batch_delete_clinical_trials(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "trials")), trace_id=req.trace_id)

    def batch_upsert_procurement_events(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "procurement")), trace_id=req.trace_id)

    def batch_delete_procurement_events(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "procurement")), trace_id=req.trace_id)

    def batch_upsert_regulatory_risks(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "risks")), trace_id=req.trace_id)

    def batch_delete_regulatory_risks(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "risks")), trace_id=req.trace_id)

    def _prepare_items(self, req: BatchItemsRequest, *, validate_stock: bool = True) -> list[dict]:
        if not req.items:
            raise ValueError("items is required")
        items = []
        for item in req.items:
            payload = dict(item)
            if validate_stock and payload.get("stock_code"):
                payload["stock_code"] = require_stock_code(payload["stock_code"])
            items.append(payload)
        return items

    def _batch_upsert(self, db, req: BatchItemsRequest, mode: str) -> dict:
        repo = AnnouncementWriteRepository(db)
        sync_status = None
        if mode == "raw":
            entities, created, updated = repo.batch_upsert_raw_announcements(self._prepare_items(req))
            if req.sync_vector_index:
                sync_status = self._sync_announcements(db, [e.id for e in entities])
        elif mode == "structured":
            entities, created, updated = repo.batch_upsert_structured_announcements(self._prepare_items(req))
        elif mode == "approvals":
            entities, created, updated = repo.batch_upsert_drug_approvals(self._prepare_items(req))
        elif mode == "trials":
            entities, created, updated = repo.batch_upsert_clinical_trials(self._prepare_items(req))
        elif mode == "procurement":
            entities, created, updated = repo.batch_upsert_procurement_events(self._prepare_items(req))
        elif mode == "risks":
            entities, created, updated = repo.batch_upsert_regulatory_risks(self._prepare_items(req))
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

    def _batch_delete(self, db, req: BatchItemsRequest, mode: str) -> dict:
        repo = AnnouncementWriteRepository(db)
        deleted_chunks = None
        if mode == "raw":
            deleted_ids = repo.batch_delete_raw_announcements(self._prepare_items(req))
            if req.sync_vector_index and deleted_ids:
                deleted_chunks = self._delete_announcement_vectors(deleted_ids)
        elif mode == "structured":
            deleted_ids = repo.batch_delete_structured_announcements(self._prepare_items(req, validate_stock=False))
        elif mode == "approvals":
            deleted_ids = repo.batch_delete_drug_approvals(self._prepare_items(req))
        elif mode == "trials":
            deleted_ids = repo.batch_delete_clinical_trials(self._prepare_items(req))
        elif mode == "procurement":
            deleted_ids = repo.batch_delete_procurement_events(self._prepare_items(req))
        elif mode == "risks":
            deleted_ids = repo.batch_delete_regulatory_risks(self._prepare_items(req))
        else:
            raise ValueError(f"unsupported mode: {mode}")
        result = {
            "deleted_count": len(deleted_ids),
            "total": len(deleted_ids),
            "ids": deleted_ids,
        }
        if deleted_chunks is not None:
            result["deleted_chunks"] = deleted_chunks
        return result

    def _sync_announcements(self, db, source_ids: list[int]) -> str:
        try:
            from app.knowledge import sync as kg_sync
            kg_sync.sync_announcements_by_ids(db, source_ids, is_hot=True)
            return "synced"
        except Exception:
            return "skipped"

    def _delete_announcement_vectors(self, source_ids: list[int]) -> int:
        return self.ctx.vector_store.delete_by_source(
            doc_type="announcement",
            source_table="announcement_raw_hot",
            source_pks=source_ids,
        )
