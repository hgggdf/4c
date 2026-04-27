from __future__ import annotations

from app.core.repositories.research_report_write_repository import ResearchReportWriteRepository

from .base import BaseService
from .write_requests import BatchItemsRequest


class ResearchReportWriteService(BaseService):
    def batch_upsert_research_reports(self, req: BatchItemsRequest):
        return self._run(lambda: self._with_db(lambda db: self._batch_upsert(db, req)), trace_id=req.trace_id)

    def _batch_upsert(self, db, req: BatchItemsRequest) -> dict:
        repo = ResearchReportWriteRepository(db)
        entities, created, updated = repo.batch_upsert_research_reports(req.items)
        return {
            "created_count": created,
            "updated_count": updated,
            "total": len(entities),
            "ids": [e.id for e in entities],
        }
