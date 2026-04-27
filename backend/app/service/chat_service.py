from __future__ import annotations

from app.core.repositories import ChatRepository

from .base import BaseService
from .guards import require_non_empty, require_positive_int, require_stock_code
from .requests import ChatAppendMessageRequest, ChatCreateSessionRequest, ChatListSessionsRequest, ChatSessionRequest, ChatUpdateCurrentStockRequest, StockCodeRequest
from .serializers import model_to_dict, normalize_value


class ChatService(BaseService):
    def __init__(self, *, ctx, company_service=None, cache_service=None) -> None:
        super().__init__(ctx=ctx)
        self.company_service = company_service
        self.cache_service = cache_service

    def get_session(self, req: ChatSessionRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_session(db, req)), trace_id=req.trace_id)

    def list_sessions(self, req: ChatListSessionsRequest):
        return self._run(lambda: self._with_db(lambda db: self._list_sessions(db, req)), trace_id=req.trace_id)

    def list_messages(self, req: ChatSessionRequest):
        return self._run(lambda: self._with_db(lambda db: self._list_messages(db, req)), trace_id=req.trace_id)

    def get_current_context(self, req: ChatSessionRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_current_context(db, req)), trace_id=req.trace_id)

    def create_session(self, req: ChatCreateSessionRequest):
        return self._run(lambda: self._with_db(lambda db: self._create_session(db, req)), trace_id=req.trace_id)

    def append_user_message(self, req: ChatAppendMessageRequest):
        return self._run(lambda: self._with_db(lambda db: self._append_message(db, req, role="user")), trace_id=req.trace_id)

    def append_assistant_message(self, req: ChatAppendMessageRequest):
        return self._run(lambda: self._with_db(lambda db: self._append_message(db, req, role="assistant")), trace_id=req.trace_id)

    def update_current_stock(self, req: ChatUpdateCurrentStockRequest):
        return self._run(lambda: self._with_db(lambda db: self._update_current_stock(db, req)), trace_id=req.trace_id)

    def delete_session(self, req: ChatSessionRequest):
        return self._run(lambda: self._with_db(lambda db: self._delete_session(db, req)), trace_id=req.trace_id)

    def _ensure_company(self, stock_code: str) -> None:
        if self.company_service:
            ok = self.company_service.ensure_company_exists(stock_code).data
            if not ok:
                raise ValueError(f"company not found: {stock_code}")

    def _get_session(self, db, req: ChatSessionRequest) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        entity = ChatRepository(db).get_session(session_id)
        if entity is None:
            raise ValueError(f"session not found: {session_id}")
        payload = model_to_dict(entity, ["id", "user_id", "session_title", "current_stock_code", "created_at", "updated_at"])
        payload["current_context"] = self._build_current_context(db, entity.id, entity.current_stock_code)
        return payload

    def _list_sessions(self, db, req: ChatListSessionsRequest) -> list[dict]:
        user_id = require_positive_int(req.user_id, "user_id")
        limit = require_positive_int(req.limit, "limit")
        rows = ChatRepository(db).list_sessions_by_user(user_id, limit=limit)
        return [self._session_payload(db, r) for r in rows]

    def _list_messages(self, db, req: ChatSessionRequest) -> list[dict]:
        session_id = require_positive_int(req.session_id, "session_id")
        rows = ChatRepository(db).list_messages(session_id)
        return [self._message_payload(r) for r in rows]

    def _get_current_context(self, db, req: ChatSessionRequest) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        cache = ChatRepository(db).get_context_cache(session_id)
        if cache is not None:
            payload = model_to_dict(cache, ["session_id", "user_id", "context_json", "created_at", "expire_at"])
            payload["stock_context"] = self._resolve_stock_context_from_cache(cache)
            return payload
        session = ChatRepository(db).get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        return {
            "session_id": session.id,
            "user_id": session.user_id,
            "context_json": {"current_stock_code": session.current_stock_code},
            "created_at": None,
            "expire_at": None,
        }

    def _create_session(self, db, req: ChatCreateSessionRequest) -> dict:
        user_id = require_positive_int(req.user_id, "user_id")
        title = req.session_title.strip() if req.session_title else None
        entity = ChatRepository(db).create_session(user_id, session_title=title)
        return self._session_payload(db, entity)

    def _append_message(self, db, req: ChatAppendMessageRequest, *, role: str) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        content = require_non_empty(req.content, "content")
        stock_code = req.stock_code.strip() if req.stock_code else None
        if stock_code:
            require_stock_code(stock_code)
            self._ensure_company(stock_code)
        entity = ChatRepository(db).append_message(
            session_id,
            role=role,
            content=content,
            stock_code=stock_code,
            intent_type=req.intent_type,
            tool_calls_json=req.tool_calls,
        )
        payload = model_to_dict(entity, ["id", "session_id", "role", "content", "stock_code", "intent_type", "tool_calls_json", "created_at"])
        payload["tool_calls_json"] = normalize_value(payload.get("tool_calls_json"))
        return payload

    def _update_current_stock(self, db, req: ChatUpdateCurrentStockRequest) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        stock_code = require_stock_code(req.stock_code)
        self._ensure_company(stock_code)
        entity = ChatRepository(db).update_current_stock(session_id, stock_code)
        if entity is None:
            raise ValueError(f"session not found: {session_id}")
        return self._session_payload(db, entity)

    def _delete_session(self, db, req: ChatSessionRequest) -> dict:
        session_id = require_positive_int(req.session_id, "session_id")
        ok = ChatRepository(db).delete_session(session_id)
        if not ok:
            raise ValueError(f"session not found: {session_id}")
        return {"deleted": True, "session_id": session_id}

    def _session_payload(self, db, entity) -> dict:
        payload = model_to_dict(entity, ["id", "user_id", "session_title", "current_stock_code", "created_at", "updated_at"])
        return payload

    def _message_payload(self, entity) -> dict:
        payload = model_to_dict(entity, ["id", "session_id", "role", "content", "stock_code", "intent_type", "tool_calls_json", "created_at"])
        payload["tool_calls_json"] = normalize_value(payload.get("tool_calls_json"))
        return payload

    def _build_current_context(self, db, session_id, stock_code) -> dict:
        return {"current_stock_code": stock_code}

    def _resolve_stock_context_from_cache(self, cache) -> dict:
        return {}
