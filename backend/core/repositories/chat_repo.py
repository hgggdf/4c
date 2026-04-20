"""聊天记录仓储。"""

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from core.database.models.chat_history import ChatHistory


class ChatRepository:
    """负责聊天记录的写入和按时间倒序查询。"""

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        question: str,
        answer: str,
        stock_code: str | None,
    ) -> ChatHistory:
        """创建一条聊天记录并立即提交。"""
        item = ChatHistory(
            user_id=user_id,
            question=question,
            answer=answer,
            stock_code=stock_code,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def list_recent(self, db: Session, user_id: int, limit: int = 20) -> list[ChatHistory]:
        """返回指定用户最近的若干条聊天记录。"""
        stmt = (
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(desc(ChatHistory.create_time))
            .limit(limit)
        )
        return list(db.scalars(stmt))
