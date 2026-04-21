"""历史归档 Archive 表 ORM 模型（仅保留主键与分区键，完整字段同 hot 表）。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import DateTime, Date, DECIMAL, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class IncomeStatementArchive(Base):
    __tablename__ = "income_statement_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_income_archive"),
        Index("idx_income_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    selling_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    admin_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    rd_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit_deducted: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BalanceSheetArchive(Base):
    __tablename__ = "balance_sheet_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_balance_archive"),
        Index("idx_balance_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    accounts_receivable: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    inventory: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    cash: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    equity: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    goodwill: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CashflowStatementArchive(Base):
    __tablename__ = "cashflow_statement_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_cashflow_archive"),
        Index("idx_cashflow_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operating_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    investing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    financing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    free_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialMetricArchive(Base):
    __tablename__ = "financial_metric_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "metric_name", name="uk_metric_archive"),
        Index("idx_metric_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialNotesArchive(Base):
    __tablename__ = "financial_notes_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "note_type", name="uk_notes_archive"),
        Index("idx_notes_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    note_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BusinessSegmentArchive(Base):
    __tablename__ = "business_segment_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "segment_name", "segment_type", name="uk_segment_archive"),
        Index("idx_segment_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    segment_name: Mapped[str] = mapped_column(String(200), nullable=False)
    segment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class StockDailyArchive(Base):
    __tablename__ = "stock_daily_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uk_stock_daily_archive"),
        Index("idx_stock_daily_archive_code_date", "stock_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnnouncementRawArchive(Base):
    __tablename__ = "announcement_raw_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_ann_raw_archive"),
        Index("idx_ann_raw_archive_code_date", "stock_code", "publish_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    announcement_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnnouncementStructuredArchive(Base):
    __tablename__ = "announcement_structured_archive"
    __table_args__ = (
        Index("idx_ann_struct_archive_ann", "announcement_id"),
        Index("idx_ann_struct_archive_code", "stock_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class DrugApprovalArchive(Base):
    __tablename__ = "drug_approval_archive"
    __table_args__ = (Index("idx_drug_approval_archive_code_date", "stock_code", "approval_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ClinicalTrialEventArchive(Base):
    __tablename__ = "clinical_trial_event_archive"
    __table_args__ = (Index("idx_clinical_archive_code_date", "stock_code", "event_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CentralizedProcurementEventArchive(Base):
    __tablename__ = "centralized_procurement_event_archive"
    __table_args__ = (Index("idx_procurement_archive_code_date", "stock_code", "event_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class RegulatoryRiskEventArchive(Base):
    __tablename__ = "regulatory_risk_event_archive"
    __table_args__ = (Index("idx_reg_risk_archive_code_date", "stock_code", "event_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class MacroIndicatorArchive(Base):
    __tablename__ = "macro_indicator_archive"
    __table_args__ = (UniqueConstraint("indicator_name", "period", name="uk_macro_archive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsRawArchive(Base):
    __tablename__ = "news_raw_archive"
    __table_args__ = (
        UniqueConstraint("news_uid", name="uk_news_uid_archive"),
        Index("idx_news_raw_archive_publish", "publish_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_uid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsStructuredArchive(Base):
    __tablename__ = "news_structured_archive"
    __table_args__ = (Index("idx_news_struct_archive_news", "news_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsIndustryMapArchive(Base):
    __tablename__ = "news_industry_map_archive"
    __table_args__ = (
        Index("idx_news_ind_map_archive_news", "news_id"),
        Index("idx_news_ind_map_archive_industry", "industry_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False)
    industry_code: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsCompanyMapArchive(Base):
    __tablename__ = "news_company_map_archive"
    __table_args__ = (
        Index("idx_news_co_map_archive_news", "news_id"),
        Index("idx_news_co_map_archive_stock", "stock_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class IndustryImpactEventArchive(Base):
    __tablename__ = "industry_impact_event_archive"
    __table_args__ = (
        Index("idx_ind_impact_archive_industry", "industry_code"),
        Index("idx_ind_impact_archive_news", "news_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_code: Mapped[str] = mapped_column(String(50), nullable=False)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
