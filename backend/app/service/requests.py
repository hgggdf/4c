from __future__ import annotations

from dataclasses import dataclass, field

from .dto import BaseRequest


@dataclass(slots=True)
class StockCodeRequest(BaseRequest):
    stock_code: str = ""


@dataclass(slots=True)
class StockCodeLimitRequest(StockCodeRequest):
    limit: int = 4


@dataclass(slots=True)
class StockCodeDaysRequest(StockCodeRequest):
    days: int = 365
    category: str | None = None


@dataclass(slots=True)
class FinancialMetricsRequest(StockCodeLimitRequest):
    metric_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FinancialSummaryRequest(StockCodeRequest):
    period_count: int = 4


@dataclass(slots=True)
class NewsRawRequest(BaseRequest):
    days: int = 30
    news_type: str | None = None


@dataclass(slots=True)
class NewsStructuredRequest(BaseRequest):
    days: int = 30
    topic_category: str | None = None


@dataclass(slots=True)
class IndustryDaysRequest(BaseRequest):
    industry_code: str = ""
    days: int = 30


@dataclass(slots=True)
class ImpactSummaryRequest(BaseRequest):
    stock_code: str | None = None
    industry_code: str | None = None
    days: int = 30


@dataclass(slots=True)
class MacroIndicatorRequest(BaseRequest):
    indicator_name: str = ""
    period: str | None = None


@dataclass(slots=True)
class MacroListRequest(BaseRequest):
    indicator_names: list[str] = field(default_factory=list)
    periods: list[str] | None = None


@dataclass(slots=True)
class MacroSummaryRequest(BaseRequest):
    indicator_names: list[str] = field(default_factory=list)
    recent_n: int = 6


@dataclass(slots=True)
class SearchRequest(BaseRequest):
    query: str = ""
    stock_code: str | None = None
    industry_code: str | None = None
    doc_types: list[str] | None = None
    top_k: int = 5


@dataclass(slots=True)
class RebuildEmbeddingsRequest(BaseRequest):
    doc_type: str = ""
    source_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class ChatListSessionsRequest(BaseRequest):
    user_id: int = 0
    limit: int = 20


@dataclass(slots=True)
class ChatSessionRequest(BaseRequest):
    session_id: int = 0


@dataclass(slots=True)
class ChatCreateSessionRequest(BaseRequest):
    user_id: int = 0
    session_title: str | None = None


@dataclass(slots=True)
class ChatAppendMessageRequest(BaseRequest):
    session_id: int = 0
    content: str = ""
    stock_code: str | None = None
    intent_type: str | None = None
    tool_calls: dict | None = None


@dataclass(slots=True)
class ChatUpdateCurrentStockRequest(BaseRequest):
    session_id: int = 0
    stock_code: str = ""


@dataclass(slots=True)
class CacheQueryRequest(BaseRequest):
    cache_key: str = ""
    ttl_seconds: int = 86400


@dataclass(slots=True)
class CacheSetQueryRequest(CacheQueryRequest):
    result: dict = field(default_factory=dict)
    user_id: int = 0
    query_text: str | None = None
    source_signature: str | None = None


@dataclass(slots=True)
class CacheGetSessionContextRequest(BaseRequest):
    session_id: int = 0


@dataclass(slots=True)
class CacheSetSessionContextRequest(BaseRequest):
    session_id: int = 0
    user_id: int = 0
    context: dict = field(default_factory=dict)
    ttl_seconds: int = 86400


@dataclass(slots=True)
class CacheGetHotDataRequest(BaseRequest):
    data_type: str = ""
    cache_key: str = ""


@dataclass(slots=True)
class CacheSetHotDataRequest(BaseRequest):
    data_type: str = ""
    cache_key: str = ""
    value: dict = field(default_factory=dict)
    ttl_seconds: int = 86400


@dataclass(slots=True)
class CacheInvalidateRequest(BaseRequest):
    cache_key: str = ""
