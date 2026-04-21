"""路由层公共请求 schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaseRequestModel(BaseModel):
	trace_id: str | None = None
	operator_id: int | None = None
	extra: dict[str, Any] = Field(default_factory=dict)


class StockCodeModel(BaseRequestModel):
	stock_code: str


class StockCodeLimitModel(StockCodeModel):
	limit: int = 4


class StockCodeDaysModel(StockCodeModel):
	days: int = 365
	category: str | None = None


class IndustryDaysModel(BaseRequestModel):
	industry_code: str
	days: int = 30


class BatchItemsModel(BaseRequestModel):
	items: list[dict] = Field(default_factory=list)
	sync_vector_index: bool = False


__all__ = [
	"BaseRequestModel",
	"StockCodeModel",
	"StockCodeLimitModel",
	"StockCodeDaysModel",
	"IndustryDaysModel",
	"BatchItemsModel",
]