"""宏观领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel, BatchItemsModel


class MacroIndicatorModel(BaseRequestModel):
	indicator_name: str
	period: str | None = None


class MacroListModel(BaseRequestModel):
	indicator_names: list[str] = Field(default_factory=list)
	periods: list[str] | None = None


class MacroSummaryModel(BaseRequestModel):
	indicator_names: list[str] = Field(default_factory=list)
	recent_n: int = 6


__all__ = [
	"BatchItemsModel",
	"MacroIndicatorModel",
	"MacroListModel",
	"MacroSummaryModel",
]