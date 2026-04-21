"""近一年宏观指标 Hot 表 ORM 模型。"""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import DateTime, DECIMAL, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.core.database.base import Base, BIGINT_PK


class MacroIndicatorHot(Base):
    __tablename__ = "macro_indicator_hot"
    __table_args__ = (
        UniqueConstraint("indicator_name", "period", name="uk_macro_hot"),
        Index("idx_macro_hot_name", "indicator_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    indicator_name: Mapped[str] = mapped_column(String(128), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
