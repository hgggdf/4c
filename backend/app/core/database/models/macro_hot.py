"""宏观指标 ORM 模型（v3）。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import Date, DateTime, DECIMAL, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class MacroIndicator(Base):
    __tablename__ = "macro_indicator"
    __table_args__ = (
        UniqueConstraint("indicator_name", "period", name="uk_macro_indicator"),
        Index("idx_category_period", "category", "period_date"),
        Index("idx_indicator_name", "indicator_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    indicator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    period_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


# 向后兼容别名
MacroIndicatorHot = MacroIndicator
MacroIndicatorArchive = MacroIndicator
