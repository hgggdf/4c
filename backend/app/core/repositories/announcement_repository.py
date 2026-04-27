from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository):
    @staticmethod
    def _since(days: int) -> date:
        return date.today() - timedelta(days=days)

    def list_raw_announcements(self, stock_code: str, *, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .order_by(AnnouncementHot.publish_date.desc()))
        return self.scalars_all(stmt)

    def get_raw_by_id(self, announcement_id: int) -> AnnouncementHot | None:
        return self.scalar_one_or_none(
            select(AnnouncementHot).where(AnnouncementHot.id == announcement_id)
        )

    # 旧版 structured 表 → 直接查 announcement_hot，key_fields_json 含结构化字段
    def list_structured_announcements(self, stock_code: str, *, category: str | None = None, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .order_by(AnnouncementHot.publish_date.desc()))
        if category:
            stmt = stmt.where(AnnouncementHot.announcement_type == category)
        return self.scalars_all(stmt)

    # 旧版事件扩展表 → 按 announcement_type 过滤 announcement_hot
    def list_drug_approvals(self, stock_code: str, *, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .where(AnnouncementHot.announcement_type == "drug_approval")
                .order_by(AnnouncementHot.publish_date.desc()))
        return self.scalars_all(stmt)

    def list_clinical_trials(self, stock_code: str, *, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .where(AnnouncementHot.announcement_type == "clinical_trial")
                .order_by(AnnouncementHot.publish_date.desc()))
        return self.scalars_all(stmt)

    def list_procurement_events(self, stock_code: str, *, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .where(AnnouncementHot.announcement_type == "centralized_procurement")
                .order_by(AnnouncementHot.publish_date.desc()))
        return self.scalars_all(stmt)

    def list_regulatory_risks(self, stock_code: str, *, days: int = 365) -> list[AnnouncementHot]:
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .where(AnnouncementHot.publish_date >= self._since(days))
                .where(AnnouncementHot.announcement_type == "regulatory_risk")
                .order_by(AnnouncementHot.publish_date.desc()))
        return self.scalars_all(stmt)
