"""向量索引表与数据任务日志表 ORM 模型（v3）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK


class VectorDocumentIndex(Base):
    __tablename__ = "vector_document_index"
    __table_args__ = (
        UniqueConstraint("source_table", "source_id", "chunk_index", name="uk_vector_source_chunk"),
        Index("idx_source_uid", "source_uid"),
        Index("idx_doc_type", "doc_type"),
        Index("idx_vdi_stock_code", "stock_code"),
        Index("idx_vdi_industry_code", "industry_code"),
        Index("idx_vdi_vector_collection", "vector_collection"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_table: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[int] = mapped_column(BIGINT_PK, nullable=False)
    source_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)

    stock_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    vector_collection: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vector_status: Mapped[str] = mapped_column(String(32), default="success", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class DataJobLog(Base):
    __tablename__ = "data_job_log"
    __table_args__ = (
        Index("idx_job_type_status", "job_type", "job_status"),
        Index("idx_target_table", "target_table"),
        Index("idx_djl_created_at", "created_at"),
        Index("idx_batch_id", "batch_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_table: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class StagingImport(Base):
    __tablename__ = "staging_import"
    __table_args__ = (
        Index("idx_staging_batch_status", "batch_id", "import_status"),
        Index("idx_staging_data_type", "data_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    import_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
