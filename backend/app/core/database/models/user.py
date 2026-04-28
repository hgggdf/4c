"""用户、会话、消息、关注列表 ORM 模型（v3）。

v3 表名：app_user / chat_history / watchlist
为兼容现有 service/router，ORM 类名保持 User / ChatSession / ChatMessage / Watchlist，
但 __tablename__ 改为 v3 规定的名称。
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, BIGINT_FK, BIGINT_PK


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="user")
    watchlists = relationship("Watchlist", back_populates="user")


class ChatSession(Base):
    """v3 对应 chat_history 的会话维度，保留 session 概念方便前端管理多会话。"""
    __tablename__ = "chat_session"
    __table_args__ = (Index("idx_chat_session_user_updated", "user_id", "updated_at"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_user.id"), nullable=False)
    session_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_stock_code: Mapped[str | None] = mapped_column(ForeignKey("company.stock_code"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")
    current_company = relationship("Company", foreign_keys=[current_stock_code])


class ChatMessage(Base):
    """v3 对应 chat_history 的消息维度。"""
    __tablename__ = "chat_history"
    __table_args__ = (
        Index("idx_chat_history_session_created", "session_id", "created_at"),
        Index("idx_chat_history_stock_code", "stock_code"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("chat_session.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(ForeignKey("company.stock_code"), nullable=True)
    intent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tool_calls_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    company = relationship("Company", foreign_keys=[stock_code])


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "stock_code", name="uk_watchlist_user_stock"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_user.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(ForeignKey("company.stock_code"), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    alert_enabled: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="watchlists")
    company = relationship("Company", foreign_keys=[stock_code])
