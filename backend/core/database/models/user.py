from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="user")
    watchlists = relationship("Watchlist", back_populates="user")
    query_caches = relationship("QueryResultCache", back_populates="user")
    session_caches = relationship("SessionContextCache", back_populates="user")
    report_caches = relationship("ReportPreviewCache", back_populates="user")


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_stock_code: Mapped[str | None] = mapped_column(ForeignKey("company_master.stock_code"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")
    current_company = relationship("CompanyMaster", back_populates="current_chat_sessions")
    context_cache = relationship("SessionContextCache", back_populates="session", uselist=False)


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_session.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(ForeignKey("company_master.stock_code"), nullable=True)
    intent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tool_calls_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    company = relationship("CompanyMaster", back_populates="chat_messages")


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(ForeignKey("company_master.stock_code"), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alert_enabled: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="watchlists")
    company = relationship("CompanyMaster", back_populates="watchlists")
