"""新闻领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel, BatchItemsModel, IndustryDaysModel, StockCodeDaysModel


class NewsRawModel(BaseRequestModel):
	days: int = 30
	news_type: str | None = None


class NewsStructuredModel(BaseRequestModel):
	days: int = 30
	topic_category: str | None = None


class ImpactSummaryModel(BaseRequestModel):
	stock_code: str | None = None
	industry_code: str | None = None
	days: int = 30


class ReplaceNewsIndustryMapModel(BaseRequestModel):
	news_id: int
	items: list[dict] = Field(default_factory=list)


class ReplaceNewsCompanyMapModel(BaseRequestModel):
	news_id: int
	items: list[dict] = Field(default_factory=list)


__all__ = [
	"BatchItemsModel",
	"StockCodeDaysModel",
	"IndustryDaysModel",
	"NewsRawModel",
	"NewsStructuredModel",
	"ImpactSummaryModel",
	"ReplaceNewsIndustryMapModel",
	"ReplaceNewsCompanyMapModel",
]