from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.database.models.macro_hot import MacroIndicator
from app.core.repositories.base import BaseRepository


class MaintenanceRepository(BaseRepository):
    HOT_ARCHIVE_PAIRS = [
        (FinancialHot,        FinancialArchive,        "report_date"),
        (AnnouncementHot,     AnnouncementArchive,     "publish_date"),
        (ResearchReportHot,   ResearchReportArchive,   "publish_date"),
        (NewsHot,             NewsArchive,             "publish_time"),
    ]

    def _copy_to_archive(self, hot_model: Any, archive_model: Any, *, date_field: str, cutoff_date: date) -> int:
        column = getattr(hot_model, date_field)
        rows = self.scalars_all(select(hot_model).where(column < cutoff_date))
        if not rows:
            return 0

        archive_cols = {c.key for c in archive_model.__table__.columns}
        count = 0
        for row in rows:
            payload = {col: getattr(row, col) for col in archive_cols if hasattr(row, col) and col != "id"}
            self.upsert(archive_model, unique_fields={"id": row.id}, values=payload)
            self.delete(row, flush=False)
            count += 1
        self.db.flush()
        return count

    def archive_before(self, cutoff_date: date) -> dict[str, int]:
        result: dict[str, int] = {}
        for hot_model, archive_model, field_name in self.HOT_ARCHIVE_PAIRS:
            result[hot_model.__tablename__] = self._copy_to_archive(
                hot_model, archive_model, date_field=field_name, cutoff_date=cutoff_date
            )
        return result

    # 旧版汇总表重建方法 → 返回空结果（v3 无汇总表，实时查询）
    def rebuild_financial_metric_summary_yearly(self, *, stock_code: str | None = None, year: int | None = None) -> dict[str, int]:
        return {"created": 0, "updated": 0, "total": 0}

    def rebuild_announcement_summary_monthly(self, *, stock_code: str | None = None, year_month: str | None = None) -> dict[str, int]:
        return {"created": 0, "updated": 0, "total": 0}

    def rebuild_drug_pipeline_summary_yearly(self, *, stock_code: str | None = None, year: int | None = None) -> dict[str, int]:
        return {"created": 0, "updated": 0, "total": 0}

    def rebuild_industry_news_summary_monthly(self, *, industry_code: str | None = None, year_month: str | None = None) -> dict[str, int]:
        return {"created": 0, "updated": 0, "total": 0}

    # 旧版缓存失效 → v3 无缓存表，直接返回
    def invalidate_stock_related_caches(self, stock_code: str) -> dict[str, int]:
        return {"report_preview_deleted": 0, "hot_data_deleted": 0, "query_cache_deleted": 0}
