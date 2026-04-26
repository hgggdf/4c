from __future__ import annotations

from app.core.repositories.base import BaseRepository


class CacheRepository(BaseRepository):
    """v3 无缓存表，所有方法返回 None / 空，保持接口兼容。"""

    def get_query_cache(self, cache_key: str):
        return None

    def upsert_query_cache(self, cache_key: str, *, user_id: int, query_text: str | None,
                           result_json: dict | None, source_signature: str | None = None, expire_at=None):
        return None

    def get_hot_data(self, data_type: str, cache_key: str):
        return None

    def upsert_hot_data(self, data_type: str, cache_key: str, *, value_json: dict | None,
                        last_update=None, expire_at=None):
        return None

    def get_report_preview(self, user_id: int, stock_code: str, report_type: str | None):
        return None

    def upsert_report_preview(self, user_id: int, stock_code: str, *, report_type: str | None,
                              report_json: dict | None, expire_at=None):
        return None
