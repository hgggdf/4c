from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.user import ChatMessage, ChatSession
from app.core.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    def get_session(self, session_id: int) -> ChatSession | None:
        return self.scalar_one_or_none(select(ChatSession).where(ChatSession.id == session_id))

    def list_sessions_by_user(self, user_id: int, *, limit: int = 20) -> list[ChatSession]:
        stmt = (select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
                .limit(limit))
        return self.scalars_all(stmt)

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        stmt = (select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()))
        return self.scalars_all(stmt)

    def create_session(self, user_id: int, *, session_title: str | None = None,
                       current_stock_code: str | None = None) -> ChatSession:
        return self.add(ChatSession(user_id=user_id, session_title=session_title,
                                    current_stock_code=current_stock_code))

    def append_message(self, session_id: int, *, role: str, content: str,
                       stock_code: str | None = None, intent_type: str | None = None,
                       tool_calls_json: dict | None = None) -> ChatMessage:
        return self.add(ChatMessage(session_id=session_id, role=role, content=content,
                                    stock_code=stock_code, intent_type=intent_type,
                                    tool_calls_json=tool_calls_json))

    def update_current_stock(self, session_id: int, stock_code: str | None) -> ChatSession | None:
        entity = self.get_session(session_id)
        if entity is None:
            return None
        entity.current_stock_code = stock_code
        self.db.flush()
        return entity

<<<<<<< Updated upstream
    def get_context_cache(self, session_id: int) -> SessionContextCache | None:
        stmt = select(SessionContextCache).where(SessionContextCache.session_id == session_id)
        return self.scalar_one_or_none(stmt)
=======
    def delete_session(self, session_id: int) -> bool:
        entity = self.get_session(session_id)
        if entity is None:
            return False
        self.db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        self.db.delete(entity)
        self.db.flush()
        return True

    # v3 无 SessionContextCache 表，context 直接存在 session 内存中
    def get_context_cache(self, session_id: int):
        return None
>>>>>>> Stashed changes

    def upsert_context_cache(self, session_id: int, user_id: int, context_json: dict, *, expire_at=None):
        return None
