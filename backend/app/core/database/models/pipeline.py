"""管线事实表与 rNPV 估值快照表 ORM 模型。

设计取舍：
- pipeline_drugs 是事实表（管线基础事实）；rNPV 算法/PoS/折现率/渗透率仍放代码里。
- rnpv_valuation_runs 是计算快照表，run_uid 作为客户端幂等键（UNIQUE），
  但语义是「同一 run_uid 允许重写结果」，不同次计算用不同 UUID 区分。
- source_table + source_id 是软关联，不建外键（来源表可能是 announcement_hot/
  research_report_hot/news_hot 等），由 evidence_text 兜底。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BIGINT_PK, BIGINT_FK


class PipelineDrug(Base):
    __tablename__ = "pipeline_drugs"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="ux_pipeline_drugs_dedup_key"),
        Index("idx_pipeline_stock", "stock_code"),
        Index("idx_pipeline_phase", "trial_phase"),
        Index("idx_pipeline_area", "therapeutic_area"),
        Index("idx_pipeline_source", "source_table", "source_id"),
        Index("idx_pipeline_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("company.stock_code"), nullable=False
    )

    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_drug_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aliases_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    indication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indication_norm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    therapeutic_area: Mapped[str | None] = mapped_column(String(64), nullable=True)

    trial_phase: Mapped[str] = mapped_column(String(32), nullable=False)
    trial_phase_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    route_of_administration: Mapped[str | None] = mapped_column(String(64), nullable=True)

    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_table: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[int | None] = mapped_column(BIGINT_FK, nullable=True)
    source_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_score: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4), nullable=False, default=Decimal("0.7000")
    )

    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vector_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


class RNPVValuationRun(Base):
    __tablename__ = "rnpv_valuation_runs"
    __table_args__ = (
        UniqueConstraint("run_uid", name="ux_rnpv_run_uid"),
        Index("idx_rnpv_stock_created", "stock_code", "created_at"),
        Index("idx_rnpv_pipeline", "pipeline_drug_id"),
        Index("idx_rnpv_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    run_uid: Mapped[str] = mapped_column(String(128), nullable=False)
    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("company.stock_code"), nullable=False
    )
    pipeline_drug_id: Mapped[int | None] = mapped_column(
        BIGINT_FK, ForeignKey("pipeline_drugs.id"), nullable=True
    )

    input_params_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    scenario_results_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_by: Mapped[str] = mapped_column(String(64), default="aiagent", nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
