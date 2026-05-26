"""管线事实表 + rNPV 快照表的访问层。

业务规则集中在 upsert_drug：
- phase 单调推进守卫（含 terminated/withdrawn 例外）
- confidence_score 单调守卫
- aliases_json 合并而非覆盖
- 任一守卫失败：维持旧值，但仍刷新 evidence_text / source / updated_at
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, select

from app.core.database.models.pipeline import PipelineDrug, RNPVValuationRun
from app.core.repositories.base import BaseRepository
from app.core.utils.dedup import prepare_dedup_record
from app.core.utils.pipeline_enums import (
    PHASE_ORDER,
    merge_aliases,
    normalize_therapeutic_area,
    normalize_trial_phase,
    phase_progresses,
)
from app.core.utils.rnpv_validator import validate_run_payload


def _to_decimal(value: Any, default: Decimal = Decimal("0.7000")) -> Decimal:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


class PipelineRepository(BaseRepository):
    def list_drugs(self, stock_code: str, *, include_inactive: bool = False) -> list[PipelineDrug]:
        stmt = select(PipelineDrug).where(PipelineDrug.stock_code == stock_code)
        if not include_inactive:
            stmt = stmt.where(PipelineDrug.is_active == 1)
        phase_rank = case(
            {
                "approved": 7,
                "nda": 6,
                "nda_rejected": 6,
                "phase3": 5,
                "phase2_3": 4,
                "phase2": 3,
                "phase1_2": 2,
                "phase1": 1,
                "preclinical": 0,
                "unknown": -1,
                "terminated": -2,
                "withdrawn": -2,
            },
            value=PipelineDrug.trial_phase,
            else_=-1,
        )
        stmt = stmt.order_by(
            phase_rank.desc(),
            PipelineDrug.confidence_score.desc(),
            PipelineDrug.updated_at.desc(),
        )
        return self.scalars_all(stmt)

    def get_by_dedup_key(self, dedup_key: str) -> PipelineDrug | None:
        return self.scalar_one_or_none(
            select(PipelineDrug).where(PipelineDrug.dedup_key == dedup_key)
        )

    def get_by_id(self, drug_id: int) -> PipelineDrug | None:
        return self.scalar_one_or_none(
            select(PipelineDrug).where(PipelineDrug.id == drug_id)
        )

    def upsert_drug(self, item: dict[str, Any]) -> tuple[PipelineDrug, bool, list[str]]:
        """upsert 一条管线记录。

        返回 (entity, created, warnings)。warnings 列出被守卫拒绝的字段；
        调用方可以决定是否把它写到日志或返回给前端。
        """
        warnings: list[str] = []

        drug_name = (item.get("drug_name") or "").strip()
        if not drug_name:
            raise ValueError("drug_name 不能为空")
        stock_code = (item.get("stock_code") or "").strip()
        if not stock_code:
            raise ValueError("stock_code 不能为空")

        canonical = (item.get("canonical_drug_name") or drug_name).strip()
        new_phase = normalize_trial_phase(item.get("trial_phase"))
        new_area = normalize_therapeutic_area(item.get("therapeutic_area"))
        new_conf = _to_decimal(item.get("confidence_score"))
        new_evidence = (item.get("evidence_text") or "").strip()

        prepared = prepare_dedup_record("pipeline_drug", {
            "stock_code": stock_code,
            "drug_name": drug_name,
            "canonical_drug_name": canonical,
            "indication": item.get("indication") or "",
            "indication_norm": item.get("indication_norm") or item.get("indication") or "",
            "therapeutic_area": new_area,
            "trial_phase": new_phase,
            "trial_phase_raw": item.get("trial_phase_raw") or item.get("trial_phase") or "",
            "route_of_administration": item.get("route_of_administration"),
            "source_type": item.get("source_type"),
            "source_url": item.get("source_url"),
            "source_table": item.get("source_table"),
            "source_id": item.get("source_id"),
            "source_uid": item.get("source_uid"),
            "evidence_text": new_evidence,
            "confidence_score": str(new_conf),
            "aliases": item.get("aliases") or [],
        })
        dedup_key = prepared["dedup_key"]
        content_hash = prepared["content_hash"]

        existing = self.get_by_dedup_key(dedup_key)
        if existing is None:
            entity = PipelineDrug(
                stock_code=stock_code,
                drug_name=drug_name,
                canonical_drug_name=canonical,
                aliases_json=merge_aliases(None, drug_name, canonical, *(item.get("aliases") or [])),
                indication=item.get("indication"),
                indication_norm=item.get("indication_norm") or item.get("indication"),
                therapeutic_area=new_area,
                trial_phase=new_phase,
                trial_phase_raw=item.get("trial_phase_raw") or item.get("trial_phase") or "",
                route_of_administration=item.get("route_of_administration"),
                source_type=item.get("source_type"),
                source_url=item.get("source_url"),
                source_table=item.get("source_table"),
                source_id=item.get("source_id"),
                source_uid=item.get("source_uid"),
                evidence_text=new_evidence,
                confidence_score=new_conf,
                dedup_key=dedup_key,
                content_hash=content_hash,
                vector_status="pending",
                is_active=1,
            )
            self.add(entity)
            return entity, True, warnings

        # 已存在：守卫后再决定哪些字段允许覆盖
        if phase_progresses(existing.trial_phase, new_phase):
            existing.trial_phase = new_phase
            if item.get("trial_phase_raw") or item.get("trial_phase"):
                existing.trial_phase_raw = item.get("trial_phase_raw") or item.get("trial_phase") or ""
        else:
            warnings.append(
                f"trial_phase 降级被拒绝：existing={existing.trial_phase} new={new_phase}"
            )

        if new_conf >= (existing.confidence_score or Decimal("0")):
            if item.get("therapeutic_area"):
                existing.therapeutic_area = new_area
            if item.get("route_of_administration"):
                existing.route_of_administration = item.get("route_of_administration")
            if item.get("indication"):
                existing.indication = item.get("indication")
            if item.get("indication_norm") or item.get("indication"):
                existing.indication_norm = item.get("indication_norm") or item.get("indication")
            existing.confidence_score = new_conf
        else:
            warnings.append(
                f"confidence 降级被拒绝：existing={existing.confidence_score} new={new_conf}"
            )

        # 来源与证据始终刷新（无损：追踪最新看到这条事实的出处）
        if item.get("source_type"):
            existing.source_type = item.get("source_type")
        if item.get("source_url"):
            existing.source_url = item.get("source_url")
        if item.get("source_table"):
            existing.source_table = item.get("source_table")
        if item.get("source_id") is not None:
            existing.source_id = item.get("source_id")
        if item.get("source_uid"):
            existing.source_uid = item.get("source_uid")
        if new_evidence:
            existing.evidence_text = new_evidence

        existing.aliases_json = merge_aliases(
            existing.aliases_json, drug_name, canonical, *(item.get("aliases") or [])
        )
        existing.content_hash = content_hash
        existing.vector_status = "pending"
        existing.is_active = 1
        existing.updated_at = datetime.now()
        self.db.flush()
        return existing, False, warnings

    def ensure_placeholder(
        self, *, stock_code: str, drug_name: str, indication: str | None = None
    ) -> PipelineDrug:
        """为 rNPV run 创建占位 drug，避免孤儿 run。"""
        entity, _, _ = self.upsert_drug({
            "stock_code": stock_code,
            "drug_name": drug_name,
            "indication": indication or "",
            "trial_phase": "unknown",
            "trial_phase_raw": "user_input",
            "source_type": "user_input",
            "evidence_text": "由 rNPV 工具创建的占位条目",
            "confidence_score": Decimal("0"),
        })
        return entity

    def soft_delete(self, drug_id: int) -> bool:
        entity = self.get_by_id(drug_id)
        if entity is None:
            return False
        entity.is_active = 0
        entity.updated_at = datetime.now()
        self.db.flush()
        return True

    # ------------------------------------------------------------------
    # rNPV run
    # ------------------------------------------------------------------

    def list_runs(
        self, stock_code: str, *, limit: int = 10, include_inactive: bool = False
    ) -> list[RNPVValuationRun]:
        stmt = select(RNPVValuationRun).where(RNPVValuationRun.stock_code == stock_code)
        if not include_inactive:
            stmt = stmt.where(RNPVValuationRun.is_active == 1)
        stmt = stmt.order_by(RNPVValuationRun.created_at.desc()).limit(max(limit, 1))
        return self.scalars_all(stmt)

    def get_run_by_uid(self, run_uid: str) -> RNPVValuationRun | None:
        return self.scalar_one_or_none(
            select(RNPVValuationRun).where(RNPVValuationRun.run_uid == run_uid)
        )

    def upsert_run(
        self,
        *,
        run_uid: str,
        stock_code: str,
        input_params: dict[str, Any],
        scenario_results: dict[str, Any],
        pipeline_drug_id: int | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
        created_by: str = "aiagent",
    ) -> tuple[RNPVValuationRun, bool]:
        validate_run_payload(
            input_params=input_params, scenario_results=scenario_results
        )

        existing = self.get_run_by_uid(run_uid)
        if existing is not None:
            existing.input_params_json = input_params
            existing.scenario_results_json = scenario_results
            existing.evidence_refs_json = evidence_refs
            existing.warnings_json = warnings
            existing.pipeline_drug_id = pipeline_drug_id
            existing.is_active = 1
            self.db.flush()
            return existing, False

        entity = RNPVValuationRun(
            run_uid=run_uid,
            stock_code=stock_code,
            pipeline_drug_id=pipeline_drug_id,
            input_params_json=input_params,
            scenario_results_json=scenario_results,
            evidence_refs_json=evidence_refs,
            warnings_json=warnings,
            created_by=created_by,
            is_active=1,
        )
        self.add(entity)
        return entity, True
