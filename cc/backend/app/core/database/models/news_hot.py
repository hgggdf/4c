"""新闻热库/冷库 ORM 模型（v3）。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class NewsHot(Base):
    __tablename__ = "news_hot"
    __table_args__ = (
        Index("idx_publish_time", "publish_time"),
        Index("idx_news_type_time", "news_type", "publish_time"),
        Index("idx_vector_status", "vector_status"),
        Index("idx_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    news_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 相关公司/行业代码列表，以及结构化分析字段（行业映射、公司映射、影响事件等）
    related_stock_codes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    related_industry_codes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class NewsArchive(Base):
    __tablename__ = "news_archive"
    __table_args__ = (
        Index("idx_news_archive_publish_time", "publish_time"),
        Index("idx_news_archive_type_time", "news_type", "publish_time"),
        Index("idx_news_archive_vector_status", "vector_status"),
        Index("idx_news_archive_query_count", "query_count"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    news_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    news_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    related_stock_codes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    related_industry_codes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


# 向后兼容别名（旧扩展表全部指向 NewsHot）
NewsRawHot = NewsHot
NewsStructuredHot = NewsHot
NewsRawArchive = NewsArchive
NewsStructuredArchive = NewsArchive


class _StubMap:
    """旧映射扩展表桩，防止 import 报错，不建表。"""
    pass


NewsIndustryMapHot = _StubMap
NewsCompanyMapHot = _StubMap
IndustryImpactEventHot = _StubMap
NewsIndustryMapArchive = _StubMap
NewsCompanyMapArchive = _StubMap
IndustryImpactEventArchive = _StubMap
