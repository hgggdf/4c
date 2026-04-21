"""公司主数据与行业主数据 ORM 模型。"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base


class CompanyMaster(Base):
    """公司主数据表，存储股票基础信息与别名。"""

    __tablename__ = "company_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    industry_level1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry_level2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="active")
    alias_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    profile = relationship("CompanyProfile", back_populates="company", uselist=False, cascade="all, delete-orphan")
    industry_maps = relationship("CompanyIndustryMap", back_populates="company", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="company")
    current_chat_sessions = relationship("ChatSession", back_populates="current_company")
    chat_messages = relationship("ChatMessage", back_populates="company")
    report_preview_caches = relationship("ReportPreviewCache", back_populates="company")


class CompanyProfile(Base):
    """公司经营概况，存储主营业务、产品线和市场定位。"""

    __tablename__ = "company_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), unique=True, nullable=False, index=True)
    business_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_products_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    main_segments_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    market_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    management_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    company = relationship("CompanyMaster", back_populates="profile")


class IndustryMaster(Base):
    """行业主数据表，支持多级行业分类。"""

    __tablename__ = "industry_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    industry_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_industry_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    industry_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    company_maps = relationship("CompanyIndustryMap", back_populates="industry", cascade="all, delete-orphan")


class CompanyIndustryMap(Base):
    """公司与行业的多对多映射表。"""

    __tablename__ = "company_industry_map"
    __table_args__ = (
        UniqueConstraint("stock_code", "industry_code", name="uk_company_industry_map"),
        Index("idx_company_industry_map_stock", "stock_code"),
        Index("idx_company_industry_map_industry", "industry_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), ForeignKey("company_master.stock_code"), nullable=False)
    industry_code: Mapped[str] = mapped_column(String(50), ForeignKey("industry_master.industry_code"), nullable=False)
    is_primary: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    company = relationship("CompanyMaster", back_populates="industry_maps")
    industry = relationship("IndustryMaster", back_populates="company_maps")
