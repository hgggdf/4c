from __future__ import annotations

from sqlalchemy import delete, select

from app.core.database.models.summary_cache import SessionContextCache
from app.core.database.models.user import ChatMessage, ChatSession
from app.core.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    def get_session(self, session_id: int) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        return self.scalar_one_or_none(stmt)

    def list_sessions_by_user(self, user_id: int, *, limit: int = 20) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        stmt = stmt.order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
        stmt = stmt.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        return self.scalars_all(stmt)

    def create_session(self, user_id: int, *, session_title: str | None = None, current_stock_code: str | None = None) -> ChatSession:
        entity = ChatSession(user_id=user_id, session_title=session_title, current_stock_code=current_stock_code)
        return self.add(entity)

    def append_message(self, session_id: int, *, role: str, content: str, stock_code: str | None = None, intent_type: str | None = None, tool_calls_json: dict | None = None) -> ChatMessage:
        entity = ChatMessage(session_id=session_id, role=role, content=content, stock_code=stock_code, intent_type=intent_type, tool_calls_json=tool_calls_json)
        self.add(entity)
        return entity

    def update_current_stock(self, session_id: int, stock_code: str | None) -> ChatSession | None:
        entity = self.get_session(session_id)
        if entity is None:
            return None
        entity.current_stock_code = stock_code
        self.db.flush()
        return entity

    def delete_session(self, session_id: int) -> bool:
        entity = self.get_session(session_id)
        if entity is None:
            return False
        self.db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        self.db.delete(entity)
        self.db.flush()
        return True

    def get_context_cache(self, session_id: int) -> SessionContextCache | None:
        stmt = select(SessionContextCache).where(SessionContextCache.session_id == session_id)
        return self.scalar_one_or_none(stmt)

    def upsert_context_cache(self, session_id: int, user_id: int, context_json: dict, *, expire_at=None) -> SessionContextCache:
        entity = self.get_context_cache(session_id)
        if entity is None:
            entity = SessionContextCache(session_id=session_id, user_id=user_id, context_json=context_json, expire_at=expire_at)
            self.add(entity)
        else:
            entity.user_id = user_id
            entity.context_json = context_json
            entity.expire_at = expire_at
            self.db.flush()
        return entity
