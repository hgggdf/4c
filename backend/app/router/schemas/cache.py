"""缓存领域请求 schema。"""

from pydantic import Field

from .common import BaseRequestModel


class CacheQueryModel(BaseRequestModel):
	cache_key: str
	ttl_seconds: int = 86400


class CacheSetQueryModel(CacheQueryModel):
	result: dict = Field(default_factory=dict)
	user_id: int = 0
	query_text: str | None = None
	source_signature: str | None = None


class CacheGetSessionContextModel(BaseRequestModel):
	session_id: int


class CacheSetSessionContextModel(BaseRequestModel):
	session_id: int
	user_id: int
	context: dict = Field(default_factory=dict)
	ttl_seconds: int = 86400


class CacheGetHotDataModel(BaseRequestModel):
	data_type: str
	cache_key: str


class CacheSetHotDataModel(BaseRequestModel):
	data_type: str
	cache_key: str
	value: dict = Field(default_factory=dict)
	ttl_seconds: int = 86400


class CacheInvalidateModel(BaseRequestModel):
	cache_key: str


__all__ = [
	"CacheQueryModel",
	"CacheSetQueryModel",
	"CacheGetSessionContextModel",
	"CacheSetSessionContextModel",
	"CacheGetHotDataModel",
	"CacheSetHotDataModel",
	"CacheInvalidateModel",
]