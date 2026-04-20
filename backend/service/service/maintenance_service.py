from __future__ import annotations

from datetime import date, timedelta

from core.repositories.maintenance_repository import MaintenanceRepository

from .base import BaseService
from .guards import require_stock_code
from .write_requests import (
    ArchiveHotDataRequest,
    InvalidateStockCacheRequest,
    RebuildAnnouncementSummaryRequest,
    RebuildDrugPipelineSummaryRequest,
    RebuildFinancialMetricSummaryRequest,
    RebuildIndustryNewsSummaryRequest,
)


class MaintenanceService(BaseService):
    def archive_hot_data(self, req: ArchiveHotDataRequest):
        return self._run(lambda: self._with_db(lambda db: self._archive_hot_data(db, req)), trace_id=req.trace_id)

    def rebuild_financial_metric_summary_yearly(self, req: RebuildFinancialMetricSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._rebuild_financial_metric_summary_yearly(db, req)), trace_id=req.trace_id)

    def rebuild_announcement_summary_monthly(self, req: RebuildAnnouncementSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._rebuild_announcement_summary_monthly(db, req)), trace_id=req.trace_id)

    def rebuild_drug_pipeline_summary_yearly(self, req: RebuildDrugPipelineSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._rebuild_drug_pipeline_summary_yearly(db, req)), trace_id=req.trace_id)

    def rebuild_industry_news_summary_monthly(self, req: RebuildIndustryNewsSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._rebuild_industry_news_summary_monthly(db, req)), trace_id=req.trace_id)

    def invalidate_stock_related_caches(self, req: InvalidateStockCacheRequest):
        return self._run(lambda: self._with_db(lambda db: self._invalidate_stock_related_caches(db, req)), trace_id=req.trace_id)

    def _archive_hot_data(self, db, req: ArchiveHotDataRequest) -> dict:
        cutoff_date = req.cutoff_date or (date.today() - timedelta(days=365))
        result = MaintenanceRepository(db).archive_before(cutoff_date)
        return {"cutoff_date": cutoff_date.isoformat(), "archived": result, "total_archived": sum(result.values())}

    def _rebuild_financial_metric_summary_yearly(self, db, req: RebuildFinancialMetricSummaryRequest) -> dict:
        stock_code = require_stock_code(req.stock_code) if req.stock_code else None
        result = MaintenanceRepository(db).rebuild_financial_metric_summary_yearly(stock_code=stock_code, year=req.year)
        result.update({"stock_code": stock_code, "year": req.year})
        return result

    def _rebuild_announcement_summary_monthly(self, db, req: RebuildAnnouncementSummaryRequest) -> dict:
        stock_code = require_stock_code(req.stock_code) if req.stock_code else None
        result = MaintenanceRepository(db).rebuild_announcement_summary_monthly(stock_code=stock_code, year_month=req.year_month)
        result.update({"stock_code": stock_code, "year_month": req.year_month})
        return result

    def _rebuild_drug_pipeline_summary_yearly(self, db, req: RebuildDrugPipelineSummaryRequest) -> dict:
        stock_code = require_stock_code(req.stock_code) if req.stock_code else None
        result = MaintenanceRepository(db).rebuild_drug_pipeline_summary_yearly(stock_code=stock_code, year=req.year)
        result.update({"stock_code": stock_code, "year": req.year})
        return result

    def _rebuild_industry_news_summary_monthly(self, db, req: RebuildIndustryNewsSummaryRequest) -> dict:
        result = MaintenanceRepository(db).rebuild_industry_news_summary_monthly(industry_code=req.industry_code, year_month=req.year_month)
        result.update({"industry_code": req.industry_code, "year_month": req.year_month})
        return result

    def _invalidate_stock_related_caches(self, db, req: InvalidateStockCacheRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        result = MaintenanceRepository(db).invalidate_stock_related_caches(stock_code)
        result["stock_code"] = stock_code
        return result
