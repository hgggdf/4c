"""研报热库/冷库 ORM 模型（v3）。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class ResearchReportHot(Base):
    __tablename__ = "research_report_hot"
    __table_args__ = (
        Index("idx_rr_scope_stock_date", "scope_type", "stock_code", "publish_date"),
        Index("idx_rr_scope_industry_date", "scope_type", "industry_code", "publish_date"),
        Index("idx_rr_vector_status", "vector_status"),
        Index("idx_rr_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    report_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_org: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class ResearchReportArchive(Base):
    __tablename__ = "research_report_archive"
    __table_args__ = (
        Index("idx_rr_archive_scope_stock_date", "scope_type", "stock_code", "publish_date"),
        Index("idx_rr_archive_scope_industry_date", "scope_type", "industry_code", "publish_date"),
        Index("idx_rr_archive_vector_status", "vector_status"),
        Index("idx_rr_archive_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    report_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_org: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
