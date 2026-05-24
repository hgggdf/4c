"""维护领域请求 schema。"""

from __future__ import annotations

from datetime import date

from .common import BaseRequestModel


class ArchiveHotDataModel(BaseRequestModel):
	cutoff_date: date | None = None


class RebuildFinancialMetricSummaryModel(BaseRequestModel):
	stock_code: str | None = None
	year: int | None = None


class RebuildAnnouncementSummaryModel(BaseRequestModel):
	stock_code: str | None = None
	year_month: str | None = None


class RebuildDrugPipelineSummaryModel(BaseRequestModel):
	stock_code: str | None = None
	year: int | None = None


class RebuildIndustryNewsSummaryModel(BaseRequestModel):
	industry_code: str | None = None
	year_month: str | None = None


class InvalidateStockCacheModel(BaseRequestModel):
	stock_code: str


__all__ = [
	"ArchiveHotDataModel",
	"RebuildFinancialMetricSummaryModel",
	"RebuildAnnouncementSummaryModel",
	"RebuildDrugPipelineSummaryModel",
	"RebuildIndustryNewsSummaryModel",
	"InvalidateStockCacheModel",
]