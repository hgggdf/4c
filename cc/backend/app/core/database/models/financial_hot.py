"""财务热库/冷库 ORM 模型（v3）。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import Date, DateTime, DECIMAL, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class FinancialHot(Base):
    __tablename__ = "financial_hot"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_financial"),
        Index("idx_stock_report_date", "stock_code", "report_date"),
        Index("idx_report_type", "report_type"),
        Index("idx_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    operating_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    selling_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    admin_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    rd_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    rd_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    operating_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    net_profit_deducted: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    debt_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    operating_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    investing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    financing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)

    # 日行情数据
    trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    change_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class FinancialArchive(Base):
    __tablename__ = "financial_archive"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "report_type", name="uk_financial_archive"),
        Index("idx_financial_archive_code_date", "stock_code", "report_date"),
        Index("idx_financial_archive_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company.stock_code"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    operating_cost: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    selling_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    admin_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    rd_expense: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    rd_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    operating_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    net_profit_deducted: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    total_assets: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    total_liabilities: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    debt_ratio: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    operating_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    investing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    financing_cashflow: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)

    # 日行情数据
    trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    open_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    change_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


# 向后兼容别名（旧 repository 仍引用这些类名，全部指向 FinancialHot）
IncomeStatementHot = FinancialHot
BalanceSheetHot = FinancialHot
CashflowStatementHot = FinancialHot
FinancialMetricHot = FinancialHot
FinancialNotesHot = FinancialHot
BusinessSegmentHot = FinancialHot
StockDailyHot = FinancialHot
IncomeStatementArchive = FinancialArchive
BalanceSheetArchive = FinancialArchive
CashflowStatementArchive = FinancialArchive
FinancialMetricArchive = FinancialArchive
FinancialNotesArchive = FinancialArchive
BusinessSegmentArchive = FinancialArchive
StockDailyArchive = FinancialArchive
