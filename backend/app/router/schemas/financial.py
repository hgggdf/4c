"""财务领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel, StockCodeLimitModel


class FinancialMetricsModel(StockCodeLimitModel):
	metric_names: list[str] = Field(default_factory=list)


class FinancialSummaryModel(BaseRequestModel):
	stock_code: str
	period_count: int = 4


class BatchUpsertFinancialModel(BaseRequestModel):
	items: list[dict] = Field(default_factory=list)
	sync_vector_index: bool = False
	invalidate_cache_for_stock_codes: bool = False


__all__ = [
	"StockCodeLimitModel",
	"FinancialMetricsModel",
	"FinancialSummaryModel",
	"BatchUpsertFinancialModel",
]