from __future__ import annotations

from typing import Any

from app.core.repositories.pipeline_repository import PipelineRepository

from .base import BaseService
from .guards import require_positive_int, require_stock_code


_TERMINAL_PHASES = {"terminated", "withdrawn"}
_RNPV_EXCLUDED_PHASES = _TERMINAL_PHASES | {"approved", "nda_rejected"}
_RNPV_PHASE_PRIORITY = {
    "phase3": 0,
    "phase2_3": 1,
    "nda": 2,
    "phase2": 3,
    "phase1_2": 4,
    "phase1": 5,
    "preclinical": 6,
    "unknown": 7,
}


class PipelineService(BaseService):
    def list_drugs(self, stock_code: str, *, include_terminal: bool = True):
        return self._run(
            lambda: self._with_db(
                lambda db: self._list_drugs(
                    db,
                    stock_code=stock_code,
                    include_terminal=include_terminal,
                )
            )
        )

    def list_rnpv_candidates(self, stock_code: str):
        return self._run(
            lambda: self._with_db(
                lambda db: self._list_rnpv_candidates(db, stock_code=stock_code)
            )
        )

    def upsert_drugs(self, items: list[dict[str, Any]]):
        return self._run(lambda: self._with_db(lambda db: self._upsert_drugs(db, items)))

    def rebuild_embeddings(self, *, stock_code: str | None = None):
        return self._run(
            lambda: self._with_db(
                lambda db: self._rebuild_embeddings(db, stock_code=stock_code)
            )
        )

    def list_runs(self, stock_code: str, *, limit: int = 10, include_inactive: bool = False):
        return self._run(
            lambda: self._with_db(
                lambda db: self._list_runs(
                    db,
                    stock_code=stock_code,
                    limit=limit,
                    include_inactive=include_inactive,
                )
            )
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
    ):
        return self._run(
            lambda: self._with_db(
                lambda db: self._upsert_run(
                    db,
                    run_uid=run_uid,
                    stock_code=stock_code,
                    input_params=input_params,
                    scenario_results=scenario_results,
                    pipeline_drug_id=pipeline_drug_id,
                    evidence_refs=evidence_refs,
                    warnings=warnings,
                    created_by=created_by,
                )
            )
        )

    def _list_drugs(
        self,
        db,
        *,
        stock_code: str,
        include_terminal: bool,
    ) -> list[dict[str, Any]]:
        stock_code = require_stock_code(stock_code)
        rows = PipelineRepository(db).list_drugs(stock_code)
        if not include_terminal:
            rows = [row for row in rows if row.trial_phase not in _TERMINAL_PHASES]
        return [self._drug_to_dict(row) for row in rows]

    def _list_rnpv_candidates(self, db, *, stock_code: str) -> list[dict[str, Any]]:
        stock_code = require_stock_code(stock_code)
        rows = PipelineRepository(db).list_drugs(stock_code)

        candidates = [
            row for row in rows
            if row.trial_phase not in _RNPV_EXCLUDED_PHASES
        ]
        if not candidates:
            candidates = [
                row for row in rows
                if row.trial_phase not in _TERMINAL_PHASES
            ]

        candidates.sort(
            key=lambda row: (
                _RNPV_PHASE_PRIORITY.get(row.trial_phase or "unknown", 50),
                -(float(row.confidence_score or 0)),
            )
        )
        return [self._drug_to_dict(row) for row in candidates]

    def _upsert_drugs(self, db, items: list[dict[str, Any]]) -> dict[str, Any]:
        repo = PipelineRepository(db)
        created = 0
        updated = 0
        warnings: list[str] = []

        for index, item in enumerate(items or [], start=1):
            try:
                _, is_new, item_warnings = repo.upsert_drug(item)
            except ValueError as exc:
                warnings.append(f"row {index}: {exc}")
                continue
            if is_new:
                created += 1
            else:
                updated += 1
            warnings.extend(f"row {index}: {warning}" for warning in item_warnings)

        return {"created": created, "updated": updated, "warnings": warnings}

    def _rebuild_embeddings(self, db, *, stock_code: str | None = None) -> dict[str, Any]:
        if stock_code:
            stock_code = require_stock_code(stock_code)
        from app.knowledge.sync import sync_pipeline_drugs

        count = sync_pipeline_drugs(db, stock_code=stock_code)
        return {"synced_chunks": count}

    def _list_runs(
        self,
        db,
        *,
        stock_code: str,
        limit: int,
        include_inactive: bool,
    ) -> list[dict[str, Any]]:
        stock_code = require_stock_code(stock_code)
        limit = require_positive_int(limit, "limit")
        rows = PipelineRepository(db).list_runs(
            stock_code,
            limit=min(limit, 100),
            include_inactive=include_inactive,
        )
        return [self._run_to_dict(row) for row in rows]

    def _upsert_run(
        self,
        db,
        *,
        run_uid: str,
        stock_code: str,
        input_params: dict[str, Any],
        scenario_results: dict[str, Any],
        pipeline_drug_id: int | None,
        evidence_refs: list[dict[str, Any]] | None,
        warnings: list[str] | None,
        created_by: str,
    ) -> dict[str, Any]:
        stock_code = require_stock_code(stock_code)
        run, _ = PipelineRepository(db).upsert_run(
            run_uid=run_uid,
            stock_code=stock_code,
            input_params=input_params,
            scenario_results=scenario_results,
            pipeline_drug_id=pipeline_drug_id,
            evidence_refs=evidence_refs,
            warnings=warnings,
            created_by=created_by,
        )
        return self._run_to_dict(run)

    @staticmethod
    def _drug_to_dict(row) -> dict[str, Any]:
        return {
            "id": row.id,
            "stock_code": row.stock_code,
            "drug_name": row.drug_name,
            "canonical_drug_name": row.canonical_drug_name,
            "aliases": row.aliases_json or [],
            "indication": row.indication,
            "indication_norm": row.indication_norm,
            "therapeutic_area": row.therapeutic_area,
            "trial_phase": row.trial_phase,
            "trial_phase_raw": row.trial_phase_raw,
            "route_of_administration": row.route_of_administration,
            "confidence_score": (
                float(row.confidence_score)
                if row.confidence_score is not None
                else None
            ),
            "source_type": row.source_type,
            "source_url": row.source_url,
            "source_table": row.source_table,
            "source_id": row.source_id,
            "source_uid": row.source_uid,
            "evidence_text": row.evidence_text,
            "vector_status": row.vector_status,
            "is_active": row.is_active,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _run_to_dict(row) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_uid": row.run_uid,
            "stock_code": row.stock_code,
            "pipeline_drug_id": row.pipeline_drug_id,
            "input_params": row.input_params_json,
            "scenario_results": row.scenario_results_json,
            "evidence_refs": row.evidence_refs_json,
            "warnings": row.warnings_json,
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }
