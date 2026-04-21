"""近一年财务报表与经营明细 Hot 表 ORM 模型。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, DECIMAL, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class IncomeStatementHot(Base):
    __tablename__ = "income_statement_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_income_hot"),
        Index("idx_income_hot_code_date", "stock_code", "report_date"),
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


class BalanceSheetHot(Base):
    __tablename__ = "balance_sheet_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_balance_hot"),
        Index("idx_balance_hot_code_date", "stock_code", "report_date"),
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


class CashflowStatementHot(Base):
    __tablename__ = "cashflow_statement_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_cashflow_hot"),
        Index("idx_cashflow_hot_code_date", "stock_code", "report_date"),
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


class FinancialMetricHot(Base):
    __tablename__ = "financial_metric_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "metric_name", name="uk_metric_hot"),
        Index("idx_metric_hot_code_date", "stock_code", "report_date"),
        Index("idx_metric_hot_name", "metric_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    calc_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_ref_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class FinancialNotesHot(Base):
    __tablename__ = "financial_notes_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "note_type", name="uk_notes_hot"),
        Index("idx_notes_hot_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    note_type: Mapped[str] = mapped_column(String(100), nullable=False)
    note_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BusinessSegmentHot(Base):
    __tablename__ = "business_segment_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "segment_name", "segment_type", name="uk_segment_hot"),
        Index("idx_segment_hot_code_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    segment_name: Mapped[str] = mapped_column(String(200), nullable=False)
    segment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    revenue_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class StockDailyHot(Base):
    __tablename__ = "stock_daily_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uk_stock_daily_hot"),
        Index("idx_stock_daily_hot_code_date", "stock_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
