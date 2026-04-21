from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import extract, select
from sqlalchemy.inspection import inspect as sa_inspect

from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
)
from app.core.database.models.archive import (
    AnnouncementRawArchive,
    AnnouncementStructuredArchive,
    BalanceSheetArchive,
    BusinessSegmentArchive,
    CashflowStatementArchive,
    CentralizedProcurementEventArchive,
    ClinicalTrialEventArchive,
    DrugApprovalArchive,
    FinancialMetricArchive,
    FinancialNotesArchive,
    IncomeStatementArchive,
    IndustryImpactEventArchive,
    MacroIndicatorArchive,
    NewsCompanyMapArchive,
    NewsIndustryMapArchive,
    NewsRawArchive,
    NewsStructuredArchive,
    RegulatoryRiskEventArchive,
    StockDailyArchive,
)
from app.core.database.models.financial_hot import (
    BalanceSheetHot,
    BusinessSegmentHot,
    CashflowStatementHot,
    FinancialMetricHot,
    FinancialNotesHot,
    IncomeStatementHot,
    StockDailyHot,
)
from app.core.database.models.macro_hot import MacroIndicatorHot
from app.core.database.models.news_hot import (
    IndustryImpactEventHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from app.core.database.models.summary_cache import (
    AnnouncementSummaryMonthly,
    DrugPipelineSummaryYearly,
    FinancialMetricSummaryYearly,
    HotDataCache,
    IndustryNewsSummaryMonthly,
    QueryResultCache,
    ReportPreviewCache,
)
from app.core.repositories.base import BaseRepository


class MaintenanceRepository(BaseRepository):
    HOT_ARCHIVE_PAIRS = [
        (IncomeStatementHot, IncomeStatementArchive, "report_date"),
        (BalanceSheetHot, BalanceSheetArchive, "report_date"),
        (CashflowStatementHot, CashflowStatementArchive, "report_date"),
        (FinancialMetricHot, FinancialMetricArchive, "report_date"),
        (FinancialNotesHot, FinancialNotesArchive, "report_date"),
        (BusinessSegmentHot, BusinessSegmentArchive, "report_date"),
        (StockDailyHot, StockDailyArchive, "trade_date"),
        (AnnouncementRawHot, AnnouncementRawArchive, "publish_date"),
        (AnnouncementStructuredHot, AnnouncementStructuredArchive, "created_at"),
        (DrugApprovalHot, DrugApprovalArchive, "approval_date"),
        (ClinicalTrialEventHot, ClinicalTrialEventArchive, "event_date"),
        # imported hot models below lazily to keep file readable
    ]

    def _copy_to_archive(self, hot_model: Any, archive_model: Any, *, date_field: str, cutoff_date: date) -> int:
        column = getattr(hot_model, date_field)
        rows = self.scalars_all(select(hot_model).where(column < cutoff_date))
        if not rows:
            return 0

        archive_columns = {c.key for c in sa_inspect(archive_model).columns}
        count = 0
        for row in rows:
            payload = {col: getattr(row, col) for col in archive_columns if hasattr(row, col)}
            unique = {"id": getattr(row, "id")}
            values = {k: v for k, v in payload.items() if k != "id"}
            self.upsert(archive_model, unique_fields=unique, values=values)
            self.delete(row, flush=False)
            count += 1
        self.db.flush()
        return count

    def archive_before(self, cutoff_date: date) -> dict[str, int]:
        from app.core.database.models.announcement_hot import CentralizedProcurementEventHot, RegulatoryRiskEventHot
        from app.core.database.models.news_hot import NewsCompanyMapHot, NewsIndustryMapHot

        pairs = self.HOT_ARCHIVE_PAIRS + [
            (CentralizedProcurementEventHot, CentralizedProcurementEventArchive, "event_date"),
            (RegulatoryRiskEventHot, RegulatoryRiskEventArchive, "event_date"),
            (MacroIndicatorHot, MacroIndicatorArchive, "created_at"),
            (NewsRawHot, NewsRawArchive, "publish_time"),
            (NewsStructuredHot, NewsStructuredArchive, "created_at"),
            (NewsIndustryMapHot, NewsIndustryMapArchive, "created_at"),
            (NewsCompanyMapHot, NewsCompanyMapArchive, "created_at"),
            (IndustryImpactEventHot, IndustryImpactEventArchive, "event_date"),
        ]

        result: dict[str, int] = {}
        for hot_model, archive_model, field_name in pairs:
            result[hot_model.__tablename__] = self._copy_to_archive(hot_model, archive_model, date_field=field_name, cutoff_date=cutoff_date)
        return result

    def rebuild_financial_metric_summary_yearly(self, *, stock_code: str | None = None, year: int | None = None) -> dict[str, int]:
        stmt = select(FinancialMetricHot)
        if stock_code:
            stmt = stmt.where(FinancialMetricHot.stock_code == stock_code)
        rows = self.scalars_all(stmt)
        grouped: dict[tuple[str, int, str], Any] = {}
        for row in rows:
            row_year = row.fiscal_year or row.report_date.year
            if year is not None and row_year != year:
                continue
            key = (row.stock_code, row_year, row.metric_name)
            current = grouped.get(key)
            if current is None or row.report_date > current.report_date:
                grouped[key] = row
        created = updated = 0
        for (code, row_year, metric_name), row in grouped.items():
            entity, is_created = self.upsert(
                FinancialMetricSummaryYearly,
                unique_fields={"stock_code": code, "year": row_year, "metric_name": metric_name},
                values={"metric_value": row.metric_value, "metric_unit": row.metric_unit, "created_at": datetime.now()},
            )
            _ = entity
            if is_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "total": len(grouped)}

    def rebuild_announcement_summary_monthly(self, *, stock_code: str | None = None, year_month: str | None = None) -> dict[str, int]:
        stmt = select(AnnouncementStructuredHot, AnnouncementRawHot).join(AnnouncementRawHot, AnnouncementStructuredHot.announcement_id == AnnouncementRawHot.id)
        if stock_code:
            stmt = stmt.where(AnnouncementStructuredHot.stock_code == stock_code)
        rows = list(self.db.execute(stmt).all())
        grouped: dict[tuple[str, str, str | None, str | None], list[AnnouncementStructuredHot]] = defaultdict(list)
        for struct, raw in rows:
            ym = (raw.publish_date or date.today()).strftime("%Y-%m")
            if year_month and ym != year_month:
                continue
            grouped[(struct.stock_code, ym, struct.category, struct.signal_type)].append(struct)
        created = updated = 0
        for (code, ym, category, signal_type), items in grouped.items():
            entity, is_created = self.upsert(
                AnnouncementSummaryMonthly,
                unique_fields={"stock_code": code, "year_month": ym, "category": category, "signal_type": signal_type},
                values={
                    "event_count": len(items),
                    "summary_json": {
                        "risk_levels": Counter((i.risk_level or "unknown") for i in items),
                        "announcement_ids": [i.announcement_id for i in items],
                    },
                    "created_at": datetime.now(),
                },
            )
            _ = entity
            if is_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "total": len(grouped)}

    def rebuild_drug_pipeline_summary_yearly(self, *, stock_code: str | None = None, year: int | None = None) -> dict[str, int]:
        approvals_stmt = select(DrugApprovalHot)
        trials_stmt = select(ClinicalTrialEventHot)
        if stock_code:
            approvals_stmt = approvals_stmt.where(DrugApprovalHot.stock_code == stock_code)
            trials_stmt = trials_stmt.where(ClinicalTrialEventHot.stock_code == stock_code)
        approvals = self.scalars_all(approvals_stmt)
        trials = self.scalars_all(trials_stmt)
        stats: dict[tuple[str, int], dict[str, Any]] = defaultdict(lambda: {"approved": 0, "phase3": 0, "phase2": 0, "innovative": 0})
        for row in approvals:
            row_year = (row.approval_date or date.today()).year
            if year is not None and row_year != year:
                continue
            bucket = stats[(row.stock_code, row_year)]
            bucket["approved"] += 1
            bucket["innovative"] += int(row.is_innovative_drug or 0)
        for row in trials:
            row_year = (row.event_date or date.today()).year
            if year is not None and row_year != year:
                continue
            bucket = stats[(row.stock_code, row_year)]
            phase = (row.trial_phase or "").lower()
            if "3" in phase:
                bucket["phase3"] += 1
            if "2" in phase:
                bucket["phase2"] += 1
        created = updated = 0
        for (code, row_year), bucket in stats.items():
            entity, is_created = self.upsert(
                DrugPipelineSummaryYearly,
                unique_fields={"stock_code": code, "year": row_year},
                values={
                    "approved_drug_count": bucket["approved"],
                    "phase3_count": bucket["phase3"],
                    "phase2_count": bucket["phase2"],
                    "innovative_drug_count": bucket["innovative"],
                    "summary_json": bucket,
                    "created_at": datetime.now(),
                },
            )
            _ = entity
            if is_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "total": len(stats)}

    def rebuild_industry_news_summary_monthly(self, *, industry_code: str | None = None, year_month: str | None = None) -> dict[str, int]:
        stmt = select(NewsIndustryMapHot, NewsRawHot).join(NewsRawHot, NewsIndustryMapHot.news_id == NewsRawHot.id)
        if industry_code:
            stmt = stmt.where(NewsIndustryMapHot.industry_code == industry_code)
        rows = list(self.db.execute(stmt).all())
        grouped: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for mapping, raw in rows:
            ym = (raw.publish_time or datetime.now()).strftime("%Y-%m")
            if year_month and ym != year_month:
                continue
            grouped[(mapping.industry_code, ym)][mapping.impact_direction or "neutral"] += 1
        created = updated = 0
        for (ind_code, ym), counter in grouped.items():
            entity, is_created = self.upsert(
                IndustryNewsSummaryMonthly,
                unique_fields={"industry_code": ind_code, "year_month": ym},
                values={
                    "positive_count": int(counter.get("positive", 0)),
                    "negative_count": int(counter.get("negative", 0)),
                    "neutral_count": int(counter.get("neutral", 0)),
                    "summary_json": dict(counter),
                    "created_at": datetime.now(),
                },
            )
            _ = entity
            if is_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "total": len(grouped)}

    def invalidate_stock_related_caches(self, stock_code: str) -> dict[str, int]:
        report_stmt = select(ReportPreviewCache).where(ReportPreviewCache.stock_code == stock_code)
        report_rows = self.scalars_all(report_stmt)
        for row in report_rows:
            self.delete(row, flush=False)

        hot_stmt = select(HotDataCache)
        hot_rows = [r for r in self.scalars_all(hot_stmt) if stock_code in (r.cache_key or "")]
        for row in hot_rows:
            self.delete(row, flush=False)

        query_stmt = select(QueryResultCache)
        query_rows = [r for r in self.scalars_all(query_stmt) if stock_code in (r.query_text or "") or stock_code in (r.source_signature or "")]
        for row in query_rows:
            self.delete(row, flush=False)
        self.db.flush()
        return {"report_preview_deleted": len(report_rows), "hot_data_deleted": len(hot_rows), "query_cache_deleted": len(query_rows)}
