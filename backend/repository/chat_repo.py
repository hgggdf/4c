from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from models.chat_history import ChatHistory


class ChatRepository:
    def create(
        self,
        db: Session,
        *,
        user_id: int,
        question: str,
        answer: str,
        stock_code: str | None,
    ) -> ChatHistory:
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
        stmt = (
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(desc(ChatHistory.create_time))
            .limit(limit)
        )
        return list(db.scalars(stmt))
