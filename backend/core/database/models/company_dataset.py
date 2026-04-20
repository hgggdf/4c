"""公司聚合资料 ORM 模型。"""

from sqlalchemy import JSON, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class CompanyDataset(Base):
    """缓存单家公司聚合后的摘要、压缩版和完整数据集。"""

    __tablename__ = "company_dataset"
    __table_args__ = (
        UniqueConstraint("symbol", name="uk_company_dataset_symbol"),
        Index("idx_company_dataset_symbol", "symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    collected_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compact_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dataset_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)