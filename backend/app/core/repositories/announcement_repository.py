from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    CentralizedProcurementEventHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
    RegulatoryRiskEventHot,
)
from app.core.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository):
    @staticmethod
    def _since(days: int) -> date:
        return date.today() - timedelta(days=days)

    def list_raw_announcements(self, stock_code: str, *, days: int = 365) -> list[AnnouncementRawHot]:
        stmt = select(AnnouncementRawHot).where(AnnouncementRawHot.stock_code == stock_code)
        stmt = stmt.where(AnnouncementRawHot.publish_date >= self._since(days))
        stmt = stmt.order_by(AnnouncementRawHot.publish_date.desc(), AnnouncementRawHot.created_at.desc())
        return self.scalars_all(stmt)

    def get_raw_by_id(self, announcement_id: int) -> AnnouncementRawHot | None:
        stmt = select(AnnouncementRawHot).where(AnnouncementRawHot.id == announcement_id).options(selectinload(AnnouncementRawHot.structured_items))
        return self.scalar_one_or_none(stmt)

    def list_structured_announcements(self, stock_code: str, *, category: str | None = None, days: int = 365) -> list[AnnouncementStructuredHot]:
        stmt = select(AnnouncementStructuredHot).where(AnnouncementStructuredHot.stock_code == stock_code)
        if category:
            stmt = stmt.where(AnnouncementStructuredHot.category == category)
        stmt = stmt.order_by(AnnouncementStructuredHot.created_at.desc())
        return self.scalars_all(stmt)

    def list_drug_approvals(self, stock_code: str, *, days: int = 365) -> list[DrugApprovalHot]:
        stmt = select(DrugApprovalHot).where(DrugApprovalHot.stock_code == stock_code)
        stmt = stmt.where(DrugApprovalHot.approval_date >= self._since(days))
        stmt = stmt.order_by(DrugApprovalHot.approval_date.desc(), DrugApprovalHot.created_at.desc())
        return self.scalars_all(stmt)

    def list_clinical_trials(self, stock_code: str, *, days: int = 365) -> list[ClinicalTrialEventHot]:
        stmt = select(ClinicalTrialEventHot).where(ClinicalTrialEventHot.stock_code == stock_code)
        stmt = stmt.where(ClinicalTrialEventHot.event_date >= self._since(days))
        stmt = stmt.order_by(ClinicalTrialEventHot.event_date.desc(), ClinicalTrialEventHot.created_at.desc())
        return self.scalars_all(stmt)

    def list_procurement_events(self, stock_code: str, *, days: int = 365) -> list[CentralizedProcurementEventHot]:
        stmt = select(CentralizedProcurementEventHot).where(CentralizedProcurementEventHot.stock_code == stock_code)
        stmt = stmt.where(CentralizedProcurementEventHot.event_date >= self._since(days))
        stmt = stmt.order_by(CentralizedProcurementEventHot.event_date.desc(), CentralizedProcurementEventHot.created_at.desc())
        return self.scalars_all(stmt)

    def list_regulatory_risks(self, stock_code: str, *, days: int = 365) -> list[RegulatoryRiskEventHot]:
        stmt = select(RegulatoryRiskEventHot).where(RegulatoryRiskEventHot.stock_code == stock_code)
        stmt = stmt.where(RegulatoryRiskEventHot.event_date >= self._since(days))
        stmt = stmt.order_by(RegulatoryRiskEventHot.event_date.desc(), RegulatoryRiskEventHot.created_at.desc())
        return self.scalars_all(stmt)
