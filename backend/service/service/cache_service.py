from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.repositories import CacheRepository

from .adapters.cache import build_cache_key
from .base import BaseService
from .guards import require_non_empty, require_positive_int
from .requests import (
    CacheGetHotDataRequest,
    CacheGetSessionContextRequest,
    CacheInvalidateRequest,
    CacheQueryRequest,
    CacheSetHotDataRequest,
    CacheSetQueryRequest,
    CacheSetSessionContextRequest,
)
from .serializers import model_to_dict


class CacheService(BaseService):
    def get_query_cache(self, req: CacheQueryRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_query_cache(db, req)), trace_id=req.trace_id)

    def set_query_cache(self, req: CacheSetQueryRequest):
        return self._run(lambda: self._with_db(lambda db: self._set_query_cache(db, req)), trace_id=req.trace_id)

    def get_session_context(self, req: CacheGetSessionContextRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_session_context(db, req)), trace_id=req.trace_id)

    def set_session_context(self, req: CacheSetSessionContextRequest):
        return self._run(lambda: self._with_db(lambda db: self._set_session_context(db, req)), trace_id=req.trace_id)

    def get_hot_data(self, req: CacheGetHotDataRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_hot_data(db, req)), trace_id=req.trace_id)

    def set_hot_data(self, req: CacheSetHotDataRequest):
        return self._run(lambda: self._with_db(lambda db: self._set_hot_data(db, req)), trace_id=req.trace_id)

    def invalidate(self, req: CacheInvalidateRequest):
        return self._run(lambda: self._with_db(lambda db: self._invalidate(db, req)), trace_id=req.trace_id)

    def _get_query_cache(self, db, req: CacheQueryRequest) -> dict | None:
        cache_key = require_non_empty(req.cache_key, "cache_key")
        row = CacheRepository(db).get_query_cache(cache_key)
        return None if row is None else model_to_dict(row, ["id", "user_id", "cache_key", "query_text", "result_json", "source_signature", "created_at", "expire_at"])

    def _set_query_cache(self, db, req: CacheSetQueryRequest) -> dict:
        cache_key = require_non_empty(req.cache_key, "cache_key")
        ttl = require_positive_int(req.ttl_seconds, "ttl_seconds")
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        row = CacheRepository(db).upsert_query_cache(cache_key, user_id=req.user_id, query_text=req.query_text, result_json=req.result, source_signature=req.source_signature, expire_at=expire_at)
        return model_to_dict(row, ["id", "user_id", "cache_key", "query_text", "result_json", "source_signature", "created_at", "expire_at"])

    def _get_session_context(self, db, req: CacheGetSessionContextRequest) -> dict | None:
        session_id = require_positive_int(req.session_id, "session_id")
        # stored in relational cache table via ChatRepository in chat service; keep adapter fallback for memory cache only
        from core.repositories import ChatRepository
        row = ChatRepository(db).get_context_cache(session_id)
        return None if row is None else model_to_dict(row, ["session_id", "user_id", "context_json", "created_at", "expire_at"])

    def _set_session_context(self, db, req: CacheSetSessionContextRequest) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        user_id = require_positive_int(req.user_id, "user_id")
        ttl = require_positive_int(req.ttl_seconds, "ttl_seconds")
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        from core.repositories import ChatRepository
        row = ChatRepository(db).upsert_context_cache(session_id, user_id, req.context, expire_at=expire_at)
        return model_to_dict(row, ["session_id", "user_id", "context_json", "created_at", "expire_at"])

    def _get_hot_data(self, db, req: CacheGetHotDataRequest) -> dict | None:
        data_type = require_non_empty(req.data_type, "data_type")
        cache_key = require_non_empty(req.cache_key, "cache_key")
        row = CacheRepository(db).get_hot_data(data_type, cache_key)
        return None if row is None else model_to_dict(row, ["id", "data_type", "cache_key", "value_json", "last_update", "expire_at"])

    def _set_hot_data(self, db, req: CacheSetHotDataRequest) -> dict:
        data_type = require_non_empty(req.data_type, "data_type")
        cache_key = require_non_empty(req.cache_key, "cache_key")
        ttl = require_positive_int(req.ttl_seconds, "ttl_seconds")
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        row = CacheRepository(db).upsert_hot_data(data_type, cache_key, value_json=req.value, last_update=datetime.now(timezone.utc), expire_at=expire_at)
        return model_to_dict(row, ["id", "data_type", "cache_key", "value_json", "last_update", "expire_at"])

    def _invalidate(self, db, req: CacheInvalidateRequest) -> dict:
        cache_key = require_non_empty(req.cache_key, "cache_key")
        removed = False
        # memory cache adapter
        try:
            removed = self.ctx.cache.delete(cache_key)
        except Exception:
            removed = False
        return {"cache_key": cache_key, "removed": removed}
