from __future__ import annotations

from typing import Any

from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    CentralizedProcurementEventHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
    RegulatoryRiskEventHot,
)
from app.core.repositories.base import BaseRepository


class AnnouncementWriteRepository(BaseRepository):
    def _batch_delete_by_keys(self, model: Any, items: list[dict], *, key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            filters = {key: item.get(key) for key in key_fields}
            rows = self.list_by(model, **filters)
            for row in rows:
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids

    def batch_upsert_raw_announcements(self, items: list[dict]):
        return self.bulk_upsert(AnnouncementRawHot, items=items, unique_keys=["stock_code", "title", "publish_date"])

    def batch_delete_raw_announcements(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(AnnouncementRawHot, items, key_fields=["stock_code", "title", "publish_date"])

    def batch_upsert_structured_announcements(self, items: list[dict]):
        return self.bulk_upsert(AnnouncementStructuredHot, items=items, unique_keys=["announcement_id", "category"])

    def batch_delete_structured_announcements(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(AnnouncementStructuredHot, items, key_fields=["announcement_id", "category"])

    def batch_upsert_drug_approvals(self, items: list[dict]):
        return self.bulk_upsert(DrugApprovalHot, items=items, unique_keys=["stock_code", "drug_name", "approval_date", "approval_type"])

    def batch_delete_drug_approvals(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(DrugApprovalHot, items, key_fields=["stock_code", "drug_name", "approval_date", "approval_type"])

    def batch_upsert_clinical_trials(self, items: list[dict]):
        return self.bulk_upsert(ClinicalTrialEventHot, items=items, unique_keys=["stock_code", "drug_name", "trial_phase", "event_date", "event_type"])

    def batch_delete_clinical_trials(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(ClinicalTrialEventHot, items, key_fields=["stock_code", "drug_name", "trial_phase", "event_date", "event_type"])

    def batch_upsert_procurement_events(self, items: list[dict]):
        return self.bulk_upsert(CentralizedProcurementEventHot, items=items, unique_keys=["stock_code", "drug_name", "procurement_round", "event_date"])

    def batch_delete_procurement_events(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(CentralizedProcurementEventHot, items, key_fields=["stock_code", "drug_name", "procurement_round", "event_date"])

    def batch_upsert_regulatory_risks(self, items: list[dict]):
        return self.bulk_upsert(RegulatoryRiskEventHot, items=items, unique_keys=["stock_code", "risk_type", "event_date"])

    def batch_delete_regulatory_risks(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(RegulatoryRiskEventHot, items, key_fields=["stock_code", "risk_type", "event_date"])
