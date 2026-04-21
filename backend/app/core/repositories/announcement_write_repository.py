from __future__ import annotations

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
    def batch_upsert_raw_announcements(self, items: list[dict]):
        return self.bulk_upsert(AnnouncementRawHot, items=items, unique_keys=["stock_code", "title", "publish_date"])

    def batch_upsert_structured_announcements(self, items: list[dict]):
        return self.bulk_upsert(AnnouncementStructuredHot, items=items, unique_keys=["announcement_id", "category"])

    def batch_upsert_drug_approvals(self, items: list[dict]):
        return self.bulk_upsert(DrugApprovalHot, items=items, unique_keys=["stock_code", "drug_name", "approval_date", "approval_type"])

    def batch_upsert_clinical_trials(self, items: list[dict]):
        return self.bulk_upsert(ClinicalTrialEventHot, items=items, unique_keys=["stock_code", "drug_name", "trial_phase", "event_date", "event_type"])

    def batch_upsert_procurement_events(self, items: list[dict]):
        return self.bulk_upsert(CentralizedProcurementEventHot, items=items, unique_keys=["stock_code", "drug_name", "procurement_round", "event_date"])

    def batch_upsert_regulatory_risks(self, items: list[dict]):
        return self.bulk_upsert(RegulatoryRiskEventHot, items=items, unique_keys=["stock_code", "risk_type", "event_date"])
