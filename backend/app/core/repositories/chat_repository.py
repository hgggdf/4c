from __future__ import annotations

from sqlalchemy import delete, select

from app.core.database.models.user import ChatMessage, ChatSession
from app.core.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    """聊天会话和消息读写入口。"""

    def get_session(self, session_id: int) -> ChatSession | None:
        """按会话 id 获取聊天会话。"""
        return self.scalar_one_or_none(select(ChatSession).where(ChatSession.id == session_id))

    def list_sessions_by_user(self, user_id: int, *, limit: int = 20) -> list[ChatSession]:
        """查询用户最近的聊天会话。"""
        stmt = (select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
                .limit(limit))
        return self.scalars_all(stmt)

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        """按创建时间顺序查询会话内消息。"""
        stmt = (select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()))
        return self.scalars_all(stmt)

    def create_session(self, user_id: int, *, session_title: str | None = None,
                       current_stock_code: str | None = None) -> ChatSession:
        """创建聊天会话。"""
        return self.add(ChatSession(user_id=user_id, session_title=session_title,
                                    current_stock_code=current_stock_code))

    def update_session_title(self, session_id: int, session_title: str) -> ChatSession | None:
        """更新会话标题。"""
        entity = self.get_session(session_id)
        if entity is None:
            return None
        entity.session_title = session_title
        self.db.flush()
        return entity

    def append_message(self, session_id: int, *, role: str, content: str,
                       stock_code: str | None = None, intent_type: str | None = None,
                       tool_calls_json: dict | None = None) -> ChatMessage:
        """向会话追加一条消息。"""
        return self.add(ChatMessage(session_id=session_id, role=role, content=content,
                                    stock_code=stock_code, intent_type=intent_type,
                                    tool_calls_json=tool_calls_json))

    def update_current_stock(self, session_id: int, stock_code: str | None) -> ChatSession | None:
        """更新会话当前关注股票。"""
        entity = self.get_session(session_id)
        if entity is None:
            return None
        entity.current_stock_code = stock_code
        self.db.flush()
        return entity

    def delete_session(self, session_id: int) -> bool:
        """删除会话及其消息。"""
        entity = self.get_session(session_id)
        if entity is None:
            return False
        self.db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        self.db.delete(entity)
        self.db.flush()
        return True

    # v3 no longer has a SessionContextCache table; context is stored in session memory.
    def get_context_cache(self, session_id: int):
        """上下文缓存兼容入口；v3 不再使用数据库缓存表。"""
        return None

    def upsert_context_cache(self, session_id: int, user_id: int, context_json: dict, *, expire_at=None):
        """上下文缓存写入兼容入口；v3 中不落库。"""
        return None
