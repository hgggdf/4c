"""检索领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel


class SearchModel(BaseRequestModel):
	query: str
	stock_code: str | None = None
	industry_code: str | None = None
	doc_types: list[str] | None = None
	top_k: int = 5


class RebuildEmbeddingsModel(BaseRequestModel):
	doc_type: str
	source_ids: list[int] = Field(default_factory=list)


__all__ = ["SearchModel", "RebuildEmbeddingsModel"]