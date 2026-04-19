from sqlalchemy import Date, DECIMAL, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class FinancialData(Base):
    __tablename__ = "financial_data"
    __table_args__ = (
        UniqueConstraint("stock_code", "year", "metric_name", name="uk_code_year_metric"),
        Index("idx_code_year", "stock_code", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class MacroIndicator(Base):
    __tablename__ = "macro_indicator"
    __table_args__ = (
        UniqueConstraint("indicator_name", "period", name="uk_indicator_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2023-Q1", "2023"
    value: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
