"""历史归档 Archive 表 ORM 模型。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import JSON, DateTime, Date, DECIMAL, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, synonym

from core.database.base import Base, BIGINT_FK, BIGINT_PK


class IncomeStatementArchive(Base):
    __tablename__ = "income_statement_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_income_archive"),
        Index("idx_income_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    selling_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    admin_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    rd_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit_deducted: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BalanceSheetArchive(Base):
    __tablename__ = "balance_sheet_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_balance_archive"),
        Index("idx_balance_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    accounts_receivable: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    inventory: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    cash: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    equity: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    goodwill: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CashflowStatementArchive(Base):
    __tablename__ = "cashflow_statement_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_cashflow_archive"),
        Index("idx_cashflow_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    operating_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    investing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    financing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    free_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialMetricArchive(Base):
    __tablename__ = "financial_metric_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "metric_name", name="uk_financial_metric_archive"),
        Index("idx_fin_metric_archive_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calc_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialNotesArchive(Base):
    __tablename__ = "financial_notes_archive"
    __table_args__ = (
        Index("idx_fin_note_archive_code_date", "stock_code", "report_date"),
        Index("idx_fin_note_archive_type", "note_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    note_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BusinessSegmentArchive(Base):
    __tablename__ = "business_segment_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "segment_name", "segment_type", name="uk_segment_archive"),
        Index("idx_segment_archive_code_date", "stock_code", "report_date"),
        Index("idx_segment_archive_name", "segment_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    segment_name: Mapped[str] = mapped_column(String(128), nullable=False)
    segment_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    revenue_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class StockDailyArchive(Base):
    __tablename__ = "stock_daily_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uk_stock_daily_archive"),
        Index("idx_stock_daily_archive_code_date", "stock_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnnouncementRawArchive(Base):
    __tablename__ = "announcement_raw_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "title", "publish_date", name="uk_ann_raw_archive"),
        Index("idx_ann_raw_archive_code_date", "stock_code", "publish_date"),
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


class AnnouncementStructuredArchive(Base):
    __tablename__ = "announcement_structured_archive"
    __table_args__ = (
        Index("idx_ann_struct_archive_ann", "announcement_id"),
        Index("idx_ann_struct_archive_code_category", "stock_code", "category"),
        Index("idx_ann_struct_archive_signal_risk", "signal_type", "risk_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_archive.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class DrugApprovalArchive(Base):
    __tablename__ = "drug_approval_archive"
    __table_args__ = (
        Index("idx_drug_approval_archive_code_date", "stock_code", "approval_date"),
        Index("idx_drug_approval_archive_drug_name", "drug_name"),
        Index("idx_drug_approval_archive_drug_stage", "drug_stage"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drug_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_innovative_drug: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_archive.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ClinicalTrialEventArchive(Base):
    __tablename__ = "clinical_trial_event_archive"
    __table_args__ = (
        Index("idx_clinical_archive_code_date", "stock_code", "event_date"),
        Index("idx_clinical_archive_drug_phase", "drug_name", "trial_phase"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trial_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_archive.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CentralizedProcurementEventArchive(Base):
    __tablename__ = "centralized_procurement_event_archive"
    __table_args__ = (
        Index("idx_procurement_archive_code_date", "stock_code", "event_date"),
        Index("idx_procurement_archive_drug_name", "drug_name"),
        Index("idx_procurement_archive_bid_result", "bid_result"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    drug_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    procurement_round: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bid_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_change_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_archive.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class RegulatoryRiskEventArchive(Base):
    __tablename__ = "regulatory_risk_event_archive"
    __table_args__ = (
        Index("idx_reg_risk_archive_code_date", "stock_code", "event_date"),
        Index("idx_reg_risk_archive_risk_type", "risk_type"),
        Index("idx_reg_risk_archive_risk_level", "risk_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    risk_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(BIGINT_FK, ForeignKey("announcement_raw_archive.id"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class MacroIndicatorArchive(Base):
    __tablename__ = "macro_indicator_archive"
    __table_args__ = (
        UniqueConstraint("indicator_name", "period", name="uk_macro_archive"),
        Index("idx_macro_archive_name", "indicator_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    indicator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsRawArchive(Base):
    __tablename__ = "news_raw_archive"
    __table_args__ = (
        UniqueConstraint("news_uid", name="uk_news_uid_archive"),
        Index("idx_news_raw_archive_publish", "publish_time"),
        Index("idx_news_raw_archive_type_publish", "news_type", "publish_time"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True, default="zh")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsStructuredArchive(Base):
    __tablename__ = "news_structured_archive"
    __table_args__ = (
        Index("idx_news_struct_archive_news", "news_id"),
        Index("idx_news_struct_archive_topic", "topic_category"),
        Index("idx_news_struct_archive_signal_impact", "signal_type", "impact_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_archive.id"), nullable=False)
    topic_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsIndustryMapArchive(Base):
    __tablename__ = "news_industry_map_archive"
    __table_args__ = (
        UniqueConstraint("news_id", "industry_code", name="uk_news_industry_map_archive"),
        Index("idx_news_ind_map_archive_news", "news_id"),
        Index("idx_news_ind_map_archive_industry_direction", "industry_code", "impact_direction"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_archive.id"), nullable=False)
    industry_code: Mapped[str] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=False)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_strength: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsCompanyMapArchive(Base):
    __tablename__ = "news_company_map_archive"
    __table_args__ = (
        UniqueConstraint("news_id", "stock_code", name="uk_news_company_map_archive"),
        Index("idx_news_co_map_archive_news", "news_id"),
        Index("idx_news_co_map_archive_stock_direction", "stock_code", "impact_direction"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_archive.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_strength: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class IndustryImpactEventArchive(Base):
    __tablename__ = "industry_impact_event_archive"
    __table_args__ = (
        Index("idx_ind_impact_archive_industry_date", "industry_code", "event_date"),
        Index("idx_ind_impact_archive_direction_level", "impact_direction", "impact_level"),
        Index("idx_ind_impact_archive_source_news", "source_news_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    industry_code: Mapped[str] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=False)
    source_news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_archive.id"), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    news_id = synonym("source_news_id")
    event_type = synonym("event_name")
