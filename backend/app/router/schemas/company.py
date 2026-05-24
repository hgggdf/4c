"""公司领域请求 schema。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from .common import BaseRequestModel


class TextResolveModel(BaseRequestModel):
	text: str


class UpsertCompanyMasterModel(BaseRequestModel):
	stock_code: str
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


class UpsertCompanyProfileModel(BaseRequestModel):
	stock_code: str
	business_summary: str | None = None
	core_products_json: list | dict | None = None
	main_segments_json: list | dict | None = None
	market_position: str | None = None
	management_summary: str | None = None
	sync_vector_index: bool = False


class DeleteCompanyProfileModel(BaseRequestModel):
	stock_code: str
	sync_vector_index: bool = False


class BatchUpsertIndustriesModel(BaseRequestModel):
	items: list[dict] = Field(default_factory=list)


class ReplaceCompanyIndustriesModel(BaseRequestModel):
	stock_code: str
	items: list[dict] = Field(default_factory=list)


class UpsertWatchlistModel(BaseRequestModel):
	user_id: int
	stock_code: str
	remark: str | None = None
	tags_json: list | dict | None = None
	alert_enabled: int = 1


class DeleteWatchlistModel(BaseRequestModel):
	user_id: int
	stock_code: str


__all__ = [
	"TextResolveModel",
	"UpsertCompanyMasterModel",
	"UpsertCompanyProfileModel",
	"DeleteCompanyProfileModel",
	"BatchUpsertIndustriesModel",
	"ReplaceCompanyIndustriesModel",
	"UpsertWatchlistModel",
	"DeleteWatchlistModel",
]