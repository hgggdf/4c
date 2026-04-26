"""公告热库/冷库 ORM 模型（v3）。"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class AnnouncementHot(Base):
    __tablename__ = "announcement_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_announcement"),
        Index("idx_stock_publish_date", "stock_code", "publish_date"),
        Index("idx_vector_status", "vector_status"),
        Index("idx_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    announcement_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_date: Mapped[date] = mapped_column(Date, nullable=False)
    announcement_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 存放所有结构化字段：药品审批、临床试验、集采、监管风险等
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class AnnouncementArchive(Base):
    __tablename__ = "announcement_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_announcement_archive"),
        Index("idx_ann_archive_code_date", "stock_code", "publish_date"),
        Index("idx_ann_archive_vector_status", "vector_status"),
        Index("idx_ann_archive_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    announcement_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_date: Mapped[date] = mapped_column(Date, nullable=False)
    announcement_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


# 向后兼容别名（旧扩展表全部指向 AnnouncementHot）
AnnouncementRawHot = AnnouncementHot
AnnouncementStructuredHot = AnnouncementHot
AnnouncementRawArchive = AnnouncementArchive
AnnouncementStructuredArchive = AnnouncementArchive


class _StubEvent:
    """旧事件扩展表桩，防止 import 报错，不建表。"""
    pass


DrugApprovalHot = _StubEvent
ClinicalTrialEventHot = _StubEvent
CentralizedProcurementEventHot = _StubEvent
RegulatoryRiskEventHot = _StubEvent
DrugApprovalArchive = _StubEvent
ClinicalTrialEventArchive = _StubEvent
CentralizedProcurementEventArchive = _StubEvent
RegulatoryRiskEventArchive = _StubEvent
