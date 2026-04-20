"""三大财务报表与财务附注 ORM 模型。"""

from datetime import date

from sqlalchemy import JSON, Date, DECIMAL, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class IncomeStatement(Base):
    """利润表结构化数据。"""

    __tablename__ = "income_statement"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_income_code_report_date"),
        Index("idx_income_code_report_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    operating_cost: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    gross_profit: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    selling_expense: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    admin_expense: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    rd_expense: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit_deducted: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class BalanceSheet(Base):
    """资产负债表结构化数据。"""

    __tablename__ = "balance_sheet"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_balance_code_report_date"),
        Index("idx_balance_code_report_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_assets: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    accounts_receivable: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    inventory: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    cash: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    equity: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class CashflowStatement(Base):
    """现金流量表结构化数据。"""

    __tablename__ = "cashflow_statement"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uk_cashflow_code_report_date"),
        Index("idx_cashflow_code_report_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    operating_cashflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    investing_cashflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    financing_cashflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FinancialNotes(Base):
    """财务附注结构化数据。"""

    __tablename__ = "financial_notes"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", "note_type", name="uk_notes_code_date_type"),
        Index("idx_notes_code_report_date", "stock_code", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    note_type: Mapped[str] = mapped_column(String(100), nullable=False)
    note_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
