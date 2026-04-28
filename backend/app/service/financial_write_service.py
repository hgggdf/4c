from __future__ import annotations

from app.core.repositories.financial_write_repository import FinancialWriteRepository

from .base import BaseService
from .guards import require_stock_code
from .write_requests import BatchUpsertFinancialRequest


class FinancialWriteService(BaseService):
    def batch_upsert_income_statements(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "income")), trace_id=req.trace_id)

    def batch_delete_income_statements(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "income")), trace_id=req.trace_id)

    def batch_upsert_balance_sheets(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "balance")), trace_id=req.trace_id)

    def batch_delete_balance_sheets(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "balance")), trace_id=req.trace_id)

    def batch_upsert_cashflow_statements(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "cashflow")), trace_id=req.trace_id)

    def batch_delete_cashflow_statements(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "cashflow")), trace_id=req.trace_id)

    def batch_upsert_financial_metrics(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "metrics")), trace_id=req.trace_id)

    def batch_delete_financial_metrics(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "metrics")), trace_id=req.trace_id)

    def batch_upsert_financial_notes(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "notes")), trace_id=req.trace_id)

    def batch_delete_financial_notes(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "notes")), trace_id=req.trace_id)

    def batch_upsert_business_segments(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "segments")), trace_id=req.trace_id)

    def batch_delete_business_segments(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "segments")), trace_id=req.trace_id)

    def batch_upsert_stock_daily(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req, "daily")), trace_id=req.trace_id)

    def batch_delete_stock_daily(self, req: BatchUpsertFinancialRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_delete(db, req, "daily")), trace_id=req.trace_id)

    def _prepare_items(self, req: BatchUpsertFinancialRequest) -> list[dict]:
        if not req.items:
            raise ValueError("items is required")
        items = []
        for item in req.items:
            payload = dict(item)
            payload["stock_code"] = require_stock_code(payload.get("stock_code"))
            items.append(payload)
        return items

    def _batch_upsert(self, db, req: BatchUpsertFinancialRequest, mode: str) -> dict:
        repo = FinancialWriteRepository(db)
        items = self._prepare_items(req)
        sync_status = None
        if mode == "income":
            entities, created, updated = repo.batch_upsert_income_statements(items)
        elif mode == "balance":
            entities, created, updated = repo.batch_upsert_balance_sheets(items)
        elif mode == "cashflow":
            entities, created, updated = repo.batch_upsert_cashflow_statements(items)
        elif mode == "metrics":
            entities, created, updated = repo.batch_upsert_financial_metrics(items)
        elif mode == "notes":
            entities, created, updated = repo.batch_upsert_financial_notes(items)
            if req.sync_vector_index:
                sync_status = self._sync_financial_notes(db, [e.id for e in entities])
        elif mode == "segments":
            entities, created, updated = repo.batch_upsert_business_segments(items)
        elif mode == "daily":
            entities, created, updated = repo.batch_upsert_stock_daily(items)
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

    def _batch_delete(self, db, req: BatchUpsertFinancialRequest, mode: str) -> dict:
        repo = FinancialWriteRepository(db)
        items = self._prepare_items(req)
        deleted_chunks = None
        if mode == "income":
            deleted_ids = repo.batch_delete_income_statements(items)
        elif mode == "balance":
            deleted_ids = repo.batch_delete_balance_sheets(items)
        elif mode == "cashflow":
            deleted_ids = repo.batch_delete_cashflow_statements(items)
        elif mode == "metrics":
            deleted_ids = repo.batch_delete_financial_metrics(items)
        elif mode == "notes":
            deleted_ids = repo.batch_delete_financial_notes(items)
            if req.sync_vector_index and deleted_ids:
                deleted_chunks = self._delete_financial_note_vectors(deleted_ids)
        elif mode == "segments":
            deleted_ids = repo.batch_delete_business_segments(items)
        elif mode == "daily":
            deleted_ids = repo.batch_delete_stock_daily(items)
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

    def _sync_financial_notes(self, db, source_ids: list[int]) -> str:
        try:
            from app.knowledge import sync as kg_sync
            kg_sync.sync_financial_notes_by_ids(db, source_ids, is_hot=True)
            return "synced"
        except Exception:
            return "skipped"

    def _delete_financial_note_vectors(self, source_ids: list[int]) -> int:
        return self.ctx.vector_store.delete_by_source(
            doc_type="financial_note",
            source_table="financial_notes_hot",
            source_pks=source_ids,
        )
