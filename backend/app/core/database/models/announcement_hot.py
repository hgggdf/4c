"""近一年公告与医药事件 Hot 表 ORM 模型。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, DECIMAL, ForeignKey, Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, BIGINT_FK, BIGINT_PK


class AnnouncementRawHot(Base):
    __tablename__ = "announcement_raw_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_ann_raw_hot"),
        Index("idx_ann_raw_hot_code_date", "stock_code", "publish_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    announcement_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    structured_items = relationship("AnnouncementStructuredHot", back_populates="announcement", cascade="all, delete-orphan")
    drug_approvals = relationship("DrugApprovalHot", back_populates="source_announcement", cascade="all, delete-orphan")
    clinical_trials = relationship("ClinicalTrialEventHot", back_populates="source_announcement", cascade="all, delete-orphan")
    procurement_events = relationship("CentralizedProcurementEventHot", back_populates="source_announcement", cascade="all, delete-orphan")
    regulatory_risks = relationship("RegulatoryRiskEventHot", back_populates="source_announcement", cascade="all, delete-orphan")


class AnnouncementStructuredHot(Base):
    __tablename__ = "announcement_structured_hot"
    __table_args__ = (
        Index("idx_ann_struct_hot_ann", "announcement_id"),
        Index("idx_ann_struct_hot_code_category", "stock_code", "category"),
        Index("idx_ann_struct_hot_signal_risk", "signal_type", "risk_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_hot.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    announcement = relationship("AnnouncementRawHot", back_populates="structured_items")


class DrugApprovalHot(Base):
    __tablename__ = "drug_approval_hot"
    __table_args__ = (
        Index("idx_drug_approval_hot_code_date", "stock_code", "approval_date"),
        Index("idx_drug_approval_hot_drug_name", "drug_name"),
        Index("idx_drug_approval_hot_drug_stage", "drug_stage"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drug_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_innovative_drug: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    review_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_hot.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    source_announcement = relationship("AnnouncementRawHot", back_populates="drug_approvals")


class ClinicalTrialEventHot(Base):
    __tablename__ = "clinical_trial_event_hot"
    __table_args__ = (
        Index("idx_clinical_hot_code_date", "stock_code", "event_date"),
        Index("idx_clinical_hot_drug_phase", "drug_name", "trial_phase"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trial_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_hot.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    source_announcement = relationship("AnnouncementRawHot", back_populates="clinical_trials")


class CentralizedProcurementEventHot(Base):
    __tablename__ = "centralized_procurement_event_hot"
    __table_args__ = (
        Index("idx_procurement_hot_code_date", "stock_code", "event_date"),
        Index("idx_procurement_hot_drug_name", "drug_name"),
        Index("idx_procurement_hot_bid_result", "bid_result"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    procurement_round: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bid_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_change_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_hot.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    source_announcement = relationship("AnnouncementRawHot", back_populates="procurement_events")


class RegulatoryRiskEventHot(Base):
    __tablename__ = "regulatory_risk_event_hot"
    __table_args__ = (
        Index("idx_reg_risk_hot_code_date", "stock_code", "event_date"),
        Index("idx_reg_risk_hot_risk_type", "risk_type"),
        Index("idx_reg_risk_hot_risk_level", "risk_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    risk_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_hot.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    source_announcement = relationship("AnnouncementRawHot", back_populates="regulatory_risks")
