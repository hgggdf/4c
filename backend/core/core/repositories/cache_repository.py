from __future__ import annotations

from sqlalchemy import select

from core.database.models.summary_cache import HotDataCache, QueryResultCache, ReportPreviewCache
from core.repositories.base import BaseRepository


class CacheRepository(BaseRepository):
    def get_query_cache(self, cache_key: str) -> QueryResultCache | None:
        stmt = select(QueryResultCache).where(QueryResultCache.cache_key == cache_key)
        return self.scalar_one_or_none(stmt)

    def upsert_query_cache(self, cache_key: str, *, user_id: int, query_text: str | None, result_json: dict | None, source_signature: str | None = None, expire_at=None) -> QueryResultCache:
        entity = self.get_query_cache(cache_key)
        if entity is None:
            entity = QueryResultCache(user_id=user_id, cache_key=cache_key, query_text=query_text, result_json=result_json, source_signature=source_signature, expire_at=expire_at)
            self.add(entity)
        else:
            entity.user_id = user_id
            entity.query_text = query_text
            entity.result_json = result_json
            entity.source_signature = source_signature
            entity.expire_at = expire_at
            self.db.flush()
        return entity

    def get_hot_data(self, data_type: str, cache_key: str) -> HotDataCache | None:
        stmt = select(HotDataCache).where(HotDataCache.data_type == data_type, HotDataCache.cache_key == cache_key)
        return self.scalar_one_or_none(stmt)

    def upsert_hot_data(self, data_type: str, cache_key: str, *, value_json: dict | None, last_update=None, expire_at=None) -> HotDataCache:
        entity = self.get_hot_data(data_type, cache_key)
        if entity is None:
            entity = HotDataCache(data_type=data_type, cache_key=cache_key, value_json=value_json, last_update=last_update, expire_at=expire_at)
            self.add(entity)
        else:
            entity.value_json = value_json
            entity.last_update = last_update
            entity.expire_at = expire_at
            self.db.flush()
        return entity

    def get_report_preview(self, user_id: int, stock_code: str, report_type: str | None) -> ReportPreviewCache | None:
        stmt = select(ReportPreviewCache).where(ReportPreviewCache.user_id == user_id, ReportPreviewCache.stock_code == stock_code, ReportPreviewCache.report_type == report_type)
        return self.scalar_first(stmt)

    def upsert_report_preview(self, user_id: int, stock_code: str, *, report_type: str | None, report_json: dict | None, expire_at=None) -> ReportPreviewCache:
        entity = self.get_report_preview(user_id, stock_code, report_type)
        if entity is None:
            entity = ReportPreviewCache(user_id=user_id, stock_code=stock_code, report_type=report_type, report_json=report_json, expire_at=expire_at)
            self.add(entity)
        else:
            entity.report_json = report_json
            entity.expire_at = expire_at
            self.db.flush()
        return entity
