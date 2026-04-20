"""聊天历史 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base


class ChatHistory(Base):
    """用户与智能体之间的问答记录。"""

    __tablename__ = "chat_history"
    __table_args__ = (
        Index("idx_user_time", "user_id", "create_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    user = relationship("User", back_populates="chat_histories")
