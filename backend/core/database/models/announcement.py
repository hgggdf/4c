"""公告及公告结构化拆解相关 ORM 模型。"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, DECIMAL, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base


class AnnouncementRaw(Base):
    """公告原始表，保存公告标题、日期、正文和来源信息。"""

    __tablename__ = "announcement_raw"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_announcement_code_title_date"),
        Index("idx_announcement_code_date", "stock_code", "publish_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    announcement_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)

    structured_items = relationship(
        "AnnouncementStructured",
        back_populates="announcement",
        cascade="all, delete-orphan",
    )
    drug_approvals = relationship(
        "DrugApproval",
        back_populates="source_announcement",
        cascade="all, delete-orphan",
    )
    capacity_expansions = relationship(
        "CapacityExpansion",
        back_populates="source_announcement",
        cascade="all, delete-orphan",
    )


class AnnouncementStructured(Base):
    """公告结构化抽取结果表，保存分类、风险等级和关键字段。"""

    __tablename__ = "announcement_structured"
    __table_args__ = (
        Index("idx_announcement_structured_announcement", "announcement_id"),
        Index("idx_announcement_structured_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(ForeignKey("announcement_raw.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    announcement = relationship("AnnouncementRaw", back_populates="structured_items")


class DrugApproval(Base):
    """药品审批公告结构化结果表。"""

    __tablename__ = "drug_approval"
    __table_args__ = (
        Index("idx_drug_approval_code_date", "stock_code", "approval_date"),
        Index("idx_drug_approval_source", "source_announcement_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approval_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(
        ForeignKey("announcement_raw.id"),
        nullable=True,
    )

    source_announcement = relationship("AnnouncementRaw", back_populates="drug_approvals")


class CapacityExpansion(Base):
    """产能扩张公告结构化结果表。"""

    __tablename__ = "capacity_expansion"
    __table_args__ = (
        Index("idx_capacity_expansion_code_year", "stock_code", "completion_year"),
        Index("idx_capacity_expansion_source", "source_announcement_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    capacity_added: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    investment_amount: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    completion_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(
        ForeignKey("announcement_raw.id"),
        nullable=True,
    )

    source_announcement = relationship("AnnouncementRaw", back_populates="capacity_expansions")
