from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository):
    @staticmethod
    def _since(days: int) -> date:
        return date.today() - timedelta(days=days)

    def _list_by_type(self, stock_code: str, *, days: int = 365, announcement_type: str | None = None, limit: int | None = None) -> list:
        hot_stmt = (select(AnnouncementHot)
                    .where(AnnouncementHot.stock_code == stock_code)
                    .where(AnnouncementHot.publish_date >= self._since(days)))
        cold_stmt = (select(AnnouncementArchive)
                     .where(AnnouncementArchive.stock_code == stock_code)
                     .where(AnnouncementArchive.publish_date >= self._since(days)))
        if announcement_type:
            hot_stmt = hot_stmt.where(AnnouncementHot.announcement_type == announcement_type)
            cold_stmt = cold_stmt.where(AnnouncementArchive.announcement_type == announcement_type)
        hot_stmt = hot_stmt.order_by(AnnouncementHot.publish_date.desc())
        cold_stmt = cold_stmt.order_by(AnnouncementArchive.publish_date.desc())
        return self._hot_cold_list(hot_stmt, cold_stmt, limit=limit)

    def list_raw_announcements(self, stock_code: str, *, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days)

    def get_raw_by_id(self, announcement_id: int) -> AnnouncementHot | AnnouncementArchive | None:
        return self._hot_cold_get(AnnouncementHot, AnnouncementArchive, announcement_id)

    def list_structured_announcements(self, stock_code: str, *, category: str | None = None, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days, announcement_type=category)

    def list_drug_approvals(self, stock_code: str, *, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days, announcement_type="drug_approval")

    def list_clinical_trials(self, stock_code: str, *, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days, announcement_type="clinical_trial")

    def list_procurement_events(self, stock_code: str, *, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days, announcement_type="centralized_procurement")

    def list_regulatory_risks(self, stock_code: str, *, days: int = 365) -> list:
        return self._list_by_type(stock_code, days=days, announcement_type="regulatory_risk")
