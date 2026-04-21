"""近一年新闻与行业影响 Hot 表 ORM 模型。"""

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, DECIMAL, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from core.core.database.base import Base, BIGINT_FK, BIGINT_PK


class NewsRawHot(Base):
    __tablename__ = "news_raw_hot"
    __table_args__ = (
        UniqueConstraint("news_uid", name="uk_news_uid_hot"),
        Index("idx_news_raw_hot_publish", "publish_time"),
        Index("idx_news_raw_hot_type_publish", "news_type", "publish_time"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True, default="zh")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    structured_items = relationship("NewsStructuredHot", back_populates="news", cascade="all, delete-orphan")
    industry_maps = relationship("NewsIndustryMapHot", back_populates="news", cascade="all, delete-orphan")
    company_maps = relationship("NewsCompanyMapHot", back_populates="news", cascade="all, delete-orphan")
    industry_impacts = relationship("IndustryImpactEventHot", back_populates="news", cascade="all, delete-orphan")


class NewsStructuredHot(Base):
    __tablename__ = "news_structured_hot"
    __table_args__ = (
        Index("idx_news_struct_hot_news", "news_id"),
        Index("idx_news_struct_hot_topic", "topic_category"),
        Index("idx_news_struct_hot_signal_impact", "signal_type", "impact_level"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_hot.id"), nullable=False)
    topic_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    news = relationship("NewsRawHot", back_populates="structured_items")


class NewsIndustryMapHot(Base):
    __tablename__ = "news_industry_map_hot"
    __table_args__ = (
        UniqueConstraint("news_id", "industry_code", name="uk_news_industry_map_hot"),
        Index("idx_news_ind_map_hot_news", "news_id"),
        Index("idx_news_ind_map_hot_industry_direction", "industry_code", "impact_direction"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_hot.id"), nullable=False)
    industry_code: Mapped[str] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=False)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_strength: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    news = relationship("NewsRawHot", back_populates="industry_maps")


class NewsCompanyMapHot(Base):
    __tablename__ = "news_company_map_hot"
    __table_args__ = (
        UniqueConstraint("news_id", "stock_code", name="uk_news_company_map_hot"),
        Index("idx_news_co_map_hot_news", "news_id"),
        Index("idx_news_co_map_hot_stock_direction", "stock_code", "impact_direction"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_hot.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), ForeignKey("company_master.stock_code"), nullable=False)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_strength: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 4), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    news = relationship("NewsRawHot", back_populates="company_maps")


class IndustryImpactEventHot(Base):
    __tablename__ = "industry_impact_event_hot"
    __table_args__ = (
        Index("idx_ind_impact_hot_industry_date", "industry_code", "event_date"),
        Index("idx_ind_impact_hot_direction_level", "impact_direction", "impact_level"),
        Index("idx_ind_impact_hot_source_news", "source_news_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    industry_code: Mapped[str] = mapped_column(String(32), ForeignKey("industry_master.industry_code"), nullable=False)
    source_news_id: Mapped[int] = mapped_column(BIGINT_FK, ForeignKey("news_raw_hot.id"), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impact_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    # 向后兼容旧代码：保留 news_id / event_type 访问名。
    news_id = synonym("source_news_id")
    event_type = synonym("event_name")

    news = relationship("NewsRawHot", back_populates="industry_impacts")
