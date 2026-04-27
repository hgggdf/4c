from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .dto import BaseRequest


@dataclass(slots=True)
class BatchItemsRequest(BaseRequest):
    items: list[dict] = field(default_factory=list)
    sync_vector_index: bool = False


@dataclass(slots=True)
class ReplaceMappingRequest(BaseRequest):
    items: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class UpsertCompanyMasterRequest(BaseRequest):
    stock_code: str = ""
    stock_name: str = ""
    full_name: str | None = None
    exchange: str | None = None
    industry_level1: str | None = None
    industry_level2: str | None = None
    listing_date: date | None = None
    status: str | None = None
    alias_json: list[str] | dict | None = None
    source_type: str | None = None
    source_url: str | None = None


@dataclass(slots=True)
class UpsertCompanyProfileRequest(BaseRequest):
    stock_code: str = ""
    business_summary: str | None = None
    core_products_json: list | dict | None = None
    main_segments_json: list | dict | None = None
    market_position: str | None = None
    management_summary: str | None = None
    sync_vector_index: bool = False


@dataclass(slots=True)
class DeleteCompanyProfileRequest(BaseRequest):
    stock_code: str = ""
    sync_vector_index: bool = False


@dataclass(slots=True)
class BatchUpsertIndustriesRequest(BaseRequest):
    items: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ReplaceCompanyIndustriesRequest(BaseRequest):
    stock_code: str = ""
    items: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class UpsertWatchlistRequest(BaseRequest):
    user_id: int = 0
    stock_code: str = ""
    remark: str | None = None
    tags_json: list | dict | None = None
    alert_enabled: int = 1


@dataclass(slots=True)
class DeleteWatchlistRequest(BaseRequest):
    user_id: int = 0
    stock_code: str = ""


@dataclass(slots=True)
class BatchUpsertFinancialRequest(BatchItemsRequest):
    invalidate_cache_for_stock_codes: bool = False


@dataclass(slots=True)
class ReplaceNewsIndustryMapRequest(BaseRequest):
    news_id: int = 0
    items: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ReplaceNewsCompanyMapRequest(BaseRequest):
    news_id: int = 0
    items: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ArchiveHotDataRequest(BaseRequest):
    cutoff_date: date | None = None


@dataclass(slots=True)
class RebuildFinancialMetricSummaryRequest(BaseRequest):
    stock_code: str | None = None
    year: int | None = None


@dataclass(slots=True)
class RebuildAnnouncementSummaryRequest(BaseRequest):
    stock_code: str | None = None
    year_month: str | None = None


@dataclass(slots=True)
class RebuildDrugPipelineSummaryRequest(BaseRequest):
    stock_code: str | None = None
    year: int | None = None


@dataclass(slots=True)
class RebuildIndustryNewsSummaryRequest(BaseRequest):
    industry_code: str | None = None
    year_month: str | None = None


@dataclass(slots=True)
class InvalidateStockCacheRequest(BaseRequest):
    stock_code: str = ""


@dataclass(slots=True)
class IngestCompanyPackageRequest(BaseRequest):
    company_master: dict | None = None
    company_profile: dict | None = None
    industries: list[dict] = field(default_factory=list)
    company_industries: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class IngestFinancialPackageRequest(BaseRequest):
    income_statements: list[dict] = field(default_factory=list)
    balance_sheets: list[dict] = field(default_factory=list)
    cashflow_statements: list[dict] = field(default_factory=list)
    financial_metrics: list[dict] = field(default_factory=list)
    financial_notes: list[dict] = field(default_factory=list)
    business_segments: list[dict] = field(default_factory=list)
    stock_daily: list[dict] = field(default_factory=list)
    sync_vector_index: bool = False


@dataclass(slots=True)
class IngestAnnouncementPackageRequest(BaseRequest):
    raw_announcements: list[dict] = field(default_factory=list)
    structured_announcements: list[dict] = field(default_factory=list)
    drug_approvals: list[dict] = field(default_factory=list)
    clinical_trials: list[dict] = field(default_factory=list)
    procurement_events: list[dict] = field(default_factory=list)
    regulatory_risks: list[dict] = field(default_factory=list)
    sync_vector_index: bool = False


@dataclass(slots=True)
class IngestNewsPackageRequest(BaseRequest):
    macro_indicators: list[dict] = field(default_factory=list)
    news_raw: list[dict] = field(default_factory=list)
    news_structured: list[dict] = field(default_factory=list)
    news_industry_maps: dict[int, list[dict]] = field(default_factory=dict)
    news_company_maps: dict[int, list[dict]] = field(default_factory=dict)
    industry_impact_events: list[dict] = field(default_factory=list)
    sync_vector_index: bool = False
