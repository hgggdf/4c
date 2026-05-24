from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository):
    """公告读库入口。

    公告采用热库 announcement_hot + 冷库 announcement_archive 双表结构。
    查询时默认按股票代码和发布日期过滤，热库不足时由 BaseRepository 补查冷库。
    """

    @staticmethod
    def _since(days: int) -> date:
        """把最近 N 天转换成发布日期下限。"""
        return date.today() - timedelta(days=days)

    def _list_by_type(self, stock_code: str, *, days: int = 365, announcement_type: str | None = None, limit: int | None = None) -> list:
        """按股票、时间范围和公告类型查询公告。

        announcement_type 为空时表示原始公告列表；有值时表示结构化事件类型。
        """
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
        """查询指定股票最近 N 天的原始公告。"""
        return self._list_by_type(stock_code, days=days)

    def get_raw_by_id(self, announcement_id: int) -> AnnouncementHot | AnnouncementArchive | None:
        """按公告 id 查询详情，热库未命中时查冷库。"""
        return self._hot_cold_get(AnnouncementHot, AnnouncementArchive, announcement_id)

    def list_structured_announcements(self, stock_code: str, *, category: str | None = None, days: int = 365) -> list:
        """按结构化分类查询公告。"""
        return self._list_by_type(stock_code, days=days, announcement_type=category)

    def list_drug_approvals(self, stock_code: str, *, days: int = 365) -> list:
        """查询药品获批类公告事件。"""
        return self._list_by_type(stock_code, days=days, announcement_type="drug_approval")

    def list_clinical_trials(self, stock_code: str, *, days: int = 365) -> list:
        """查询临床试验类公告事件。"""
        return self._list_by_type(stock_code, days=days, announcement_type="clinical_trial")

    def list_procurement_events(self, stock_code: str, *, days: int = 365) -> list:
        """查询集采类公告事件。"""
        return self._list_by_type(stock_code, days=days, announcement_type="centralized_procurement")

    def list_regulatory_risks(self, stock_code: str, *, days: int = 365) -> list:
        """查询监管风险类公告事件。"""
        return self._list_by_type(stock_code, days=days, announcement_type="regulatory_risk")
