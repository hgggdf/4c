"""历史汇总 Summary 表与 Cache 层 ORM 模型。"""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import JSON, DateTime, DECIMAL, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base


# ── Summary 表 ────────────────────────────────────────────────────────────────

class StockDailySummaryYearly(Base):
    __tablename__ = "stock_daily_summary_yearly"
    __table_args__ = (
        UniqueConstraint("stock_code", "year", name="uk_stock_daily_summary_yearly"),
        Index("idx_stock_daily_summary_yearly_code", "stock_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_open: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    avg_close: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    max_high: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    min_low: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    avg_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_return_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialMetricSummaryYearly(Base):
    __tablename__ = "financial_metric_summary_yearly"
    __table_args__ = (
        UniqueConstraint("stock_code", "year", "metric_name", name="uk_financial_metric_summary_yearly"),
        Index("idx_financial_metric_summary_yearly_code", "stock_code", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AnnouncementSummaryMonthly(Base):
    __tablename__ = "announcement_summary_monthly"
    __table_args__ = (
        UniqueConstraint("stock_code", "year_month", "category", "signal_type", name="uk_ann_summary_monthly"),
        Index("idx_ann_summary_monthly_code", "stock_code", "year_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class DrugPipelineSummaryYearly(Base):
    __tablename__ = "drug_pipeline_summary_yearly"
    __table_args__ = (
        UniqueConstraint("stock_code", "year", name="uk_drug_pipeline_summary_yearly"),
        Index("idx_drug_pipeline_summary_yearly_code", "stock_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_drug_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    phase3_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    phase2_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    innovative_drug_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class NewsSummaryMonthly(Base):
    __tablename__ = "news_summary_monthly"
    __table_args__ = (
        UniqueConstraint("year_month", "topic_category", "industry_code", "sentiment_label", name="uk_news_summary_monthly"),
        Index("idx_news_summary_monthly_industry", "industry_code", "year_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    topic_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(50), ForeignKey("industry_master.industry_code"), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    news_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class IndustryImpactSummaryMonthly(Base):
    __tablename__ = "industry_impact_summary_monthly"
    __table_args__ = (
        UniqueConstraint("year_month", "industry_code", "impact_direction", "impact_level", name="uk_ind_impact_summary_monthly"),
        Index("idx_ind_impact_summary_monthly_industry", "industry_code", "year_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    industry_code: Mapped[str] = mapped_column(String(50), ForeignKey("industry_master.industry_code"), nullable=False)
    impact_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


# ── Cache 层 ──────────────────────────────────────────────────────────────────

class QueryResultCache(Base):
    __tablename__ = "query_result_cache"
    __table_args__ = (
        UniqueConstraint("cache_key", name="uk_query_result_cache_key"),
        Index("idx_query_result_cache_user", "user_id"),
        Index("idx_query_result_cache_expire", "expire_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    query_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_signature: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="query_caches")


class HotDataCache(Base):
    __tablename__ = "hot_data_cache"
    __table_args__ = (
        UniqueConstraint("data_type", "cache_key", name="uk_hot_data_cache"),
        Index("idx_hot_data_cache_expire", "expire_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(200), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SessionContextCache(Base):
    __tablename__ = "session_context_cache"
    __table_args__ = (Index("idx_session_context_cache_user", "user_id"),)

    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_session.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="session_caches")
    session = relationship("ChatSession", back_populates="context_cache")


class ReportPreviewCache(Base):
    __tablename__ = "report_preview_cache"
    __table_args__ = (
        Index("idx_report_preview_cache_user", "user_id"),
        Index("idx_report_preview_cache_stock", "stock_code"),
        Index("idx_report_preview_cache_expire", "expire_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    report_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="report_caches")
    company = relationship("CompanyMaster", back_populates="report_preview_caches")
