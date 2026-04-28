"""集成写入领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel


class IngestCompanyPackageModel(BaseRequestModel):
	company_master: dict | None = None
	company_profile: dict | None = None
	industries: list[dict] = Field(default_factory=list)
	company_industries: list[dict] = Field(default_factory=list)


class IngestFinancialPackageModel(BaseRequestModel):
	income_statements: list[dict] = Field(default_factory=list)
	balance_sheets: list[dict] = Field(default_factory=list)
	cashflow_statements: list[dict] = Field(default_factory=list)
	financial_metrics: list[dict] = Field(default_factory=list)
	financial_notes: list[dict] = Field(default_factory=list)
	business_segments: list[dict] = Field(default_factory=list)
	stock_daily: list[dict] = Field(default_factory=list)
	sync_vector_index: bool = False


class IngestAnnouncementPackageModel(BaseRequestModel):
	raw_announcements: list[dict] = Field(default_factory=list)
	structured_announcements: list[dict] = Field(default_factory=list)
	drug_approvals: list[dict] = Field(default_factory=list)
	clinical_trials: list[dict] = Field(default_factory=list)
	procurement_events: list[dict] = Field(default_factory=list)
	regulatory_risks: list[dict] = Field(default_factory=list)
	sync_vector_index: bool = False


class IngestNewsPackageModel(BaseRequestModel):
	macro_indicators: list[dict] = Field(default_factory=list)
	news_raw: list[dict] = Field(default_factory=list)
	news_structured: list[dict] = Field(default_factory=list)
	news_industry_maps: dict[int, list[dict]] = Field(default_factory=dict)
	news_company_maps: dict[int, list[dict]] = Field(default_factory=dict)
	industry_impact_events: list[dict] = Field(default_factory=list)
	sync_vector_index: bool = False


__all__ = [
	"IngestCompanyPackageModel",
	"IngestFinancialPackageModel",
	"IngestAnnouncementPackageModel",
	"IngestNewsPackageModel",
]