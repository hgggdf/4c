"""股票日线行情 ORM 模型。"""

from datetime import date

from sqlalchemy import BigInteger, Date, DECIMAL, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class StockDaily(Base):
    """按股票代码和交易日存储的日线行情数据。"""

    __tablename__ = "stock_daily"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uk_code_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    close: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    high: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    low: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
