from __future__ import annotations

from app.core.repositories.macro_write_repository import MacroWriteRepository

from .base import BaseService
from .write_requests import BatchItemsRequest


class MacroWriteService(BaseService):
    def batch_upsert_macro_indicators(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert_macro_indicators(db, req)), trace_id=req.trace_id)

    def _batch_upsert_macro_indicators(self, db, req: BatchItemsRequest) -> dict:
        if not req.items:
            raise ValueError("items is required")
        entities, created, updated = MacroWriteRepository(db).batch_upsert_macro_indicators(req.items)
        return {
            "created_count": created,
            "updated_count": updated,
            "total": len(entities),
            "ids": [e.id for e in entities],
        }
