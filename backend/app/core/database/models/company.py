"""公司与行业基础数据 ORM 模型（v3）。"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class IndustryMaster(Base):
    __tablename__ = "industry_master"
    __table_args__ = (
        Index("idx_industry_name", "industry_name"),
        Index("idx_parent_industry_code", "parent_industry_code"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    industry_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    industry_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_industry_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class Company(Base):
    __tablename__ = "company"
    __table_args__ = (
        Index("idx_stock_name", "stock_name"),
        Index("idx_industry_code", "industry_code"),
        Index("idx_industry_level2", "industry_level2"),
    )

    stock_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    stock_name: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industry_level1: Mapped[str | None] = mapped_column(String(64), default="医药生物", nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=True)
    industry_level2: Mapped[str | None] = mapped_column(String(64), nullable=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_products_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    main_segments_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 向后兼容属性（只保留不与列名冲突的属性）
    @property
    def profile(self):
        return self

    @property
    def alias_json(self):
        return None

    @property
    def status(self):
        return "active"

    @property
    def source_type(self):
        return None

    @property
    def source_url(self):
        return None

    @property
    def market_position(self):
        return None

    @property
    def management_summary(self):
        return None

    @property
    def industry_level(self):
        return None


# 向后兼容别名
CompanyMaster = Company
CompanyProfile = Company


class CompanyIndustryMap:
    """已废弃，仅保留以防旧 import 报错。"""
    pass
