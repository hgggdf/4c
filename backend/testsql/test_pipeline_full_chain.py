from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from agent.tools.rnpv_tools import calculate_pipeline_rnpv, list_pipeline_drugs
from app.core.database.models.company import Company
from app.core.database.models.pipeline import PipelineDrug
from app.core.database.models.vector_and_job import VectorDocumentIndex
from app.core.database.session import SessionLocal, engine
from app.service.container import ServiceContainer
from import_batch import process_batch
from main import app


RUN_ID = time.strftime("%m%d%H%M%S")
STOCK_CODE = f"88{int(time.time()) % 10000:04d}"
STOCK_NAME = f"CodexPipeline{RUN_ID}"
DRUG_MAIN = f"CODX-P3-{RUN_ID}"
DRUG_API = f"CODX-NDA-{RUN_ID}"
DRUG_IMPORT = f"CODX-IMP-{RUN_ID}"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def print_step(message: str) -> None:
    print(f"[pipeline-full-chain] {message}")


def ensure_test_company() -> None:
    with SessionLocal() as db:
        company = db.get(Company, STOCK_CODE)
        if company is None:
            db.add(
                Company(
                    stock_code=STOCK_CODE,
                    stock_name=STOCK_NAME,
                    full_name=f"{STOCK_NAME} Test Co., Ltd.",
                    exchange="TEST",
                    industry_level1="pharma",
                    industry_level2="biotech",
                    business_summary="pipeline integration test company",
                )
            )
        else:
            company.stock_name = STOCK_NAME
        db.commit()


def check_schema() -> None:
    insp = inspect(engine)
    for table in ("pipeline_drugs", "rnpv_valuation_runs"):
        assert_true(insp.has_table(table), f"missing table: {table}")
    print_step("schema exists: pipeline_drugs, rnpv_valuation_runs")


def check_service_write_query() -> int:
    container = ServiceContainer.build_default()

    created = container.pipeline.upsert_drugs(
        [
            {
                "stock_code": STOCK_CODE,
                "drug_name": DRUG_MAIN,
                "canonical_drug_name": DRUG_MAIN,
                "aliases": [f"{DRUG_MAIN}-A"],
                "indication": "solid tumor",
                "indication_norm": "solid tumor",
                "therapeutic_area": "oncology",
                "trial_phase": "phase2",
                "trial_phase_raw": "phase2",
                "route_of_administration": "injection",
                "source_type": "service_test",
                "source_url": "https://codex.test/pipeline/service",
                "evidence_text": "initial phase2 evidence",
                "confidence_score": 0.82,
            }
        ]
    )
    assert_true(created.success, f"service upsert failed: {created.message}")
    assert_true((created.data or {}).get("created", 0) + (created.data or {}).get("updated", 0) >= 1, "service upsert wrote no rows")

    downgraded = container.pipeline.upsert_drugs(
        [
            {
                "stock_code": STOCK_CODE,
                "drug_name": DRUG_MAIN,
                "canonical_drug_name": DRUG_MAIN,
                "aliases": [f"{DRUG_MAIN}-B"],
                "indication": "solid tumor",
                "indication_norm": "solid tumor",
                "therapeutic_area": "oncology",
                "trial_phase": "phase1",
                "trial_phase_raw": "phase1",
                "route_of_administration": "oral",
                "source_type": "service_test",
                "source_url": "https://codex.test/pipeline/downgrade",
                "evidence_text": "downgrade attempt should not lower phase or confidence",
                "confidence_score": 0.40,
            }
        ]
    )
    assert_true(downgraded.success, f"downgrade upsert failed: {downgraded.message}")
    warnings = " ".join((downgraded.data or {}).get("warnings", []))
    assert_true("trial_phase" in warnings, "phase downgrade guard did not warn")
    assert_true("confidence" in warnings, "confidence downgrade guard did not warn")

    promoted = container.pipeline.upsert_drugs(
        [
            {
                "stock_code": STOCK_CODE,
                "drug_name": DRUG_MAIN,
                "canonical_drug_name": DRUG_MAIN,
                "aliases": [f"{DRUG_MAIN}-C"],
                "indication": "solid tumor",
                "indication_norm": "solid tumor",
                "therapeutic_area": "oncology",
                "trial_phase": "phase3",
                "trial_phase_raw": "phase3",
                "route_of_administration": "injection",
                "source_type": "service_test",
                "source_url": "https://codex.test/pipeline/promote",
                "evidence_text": "promoted to phase3",
                "confidence_score": 0.91,
            }
        ]
    )
    assert_true(promoted.success, f"promotion upsert failed: {promoted.message}")

    listed = container.pipeline.list_drugs(STOCK_CODE)
    assert_true(listed.success, f"service list failed: {listed.message}")
    main = next((item for item in listed.data or [] if item["drug_name"] == DRUG_MAIN), None)
    assert_true(main is not None, "service list did not return main drug")
    assert_true(main["trial_phase"] == "phase3", f"phase guard/promote wrong: {main['trial_phase']}")
    assert_true(abs(float(main["confidence_score"]) - 0.91) < 0.0001, f"confidence guard/promote wrong: {main['confidence_score']}")
    assert_true(f"{DRUG_MAIN}-B" in main["aliases"] and f"{DRUG_MAIN}-C" in main["aliases"], "aliases were not merged")

    candidates = container.pipeline.list_rnpv_candidates(STOCK_CODE)
    assert_true(candidates.success, f"candidate list failed: {candidates.message}")
    assert_true((candidates.data or [])[0]["drug_name"] == DRUG_MAIN, "rNPV candidate ordering did not prioritize phase3")

    print_step("service upsert/query/guard/candidate checks passed")
    return int(main["id"])


def check_api_write_query() -> None:
    client = TestClient(app)
    payload = {
        "items": [
            {
                "stock_code": STOCK_CODE,
                "drug_name": DRUG_API,
                "canonical_drug_name": DRUG_API,
                "aliases": [f"{DRUG_API}-alias"],
                "indication": "hematology",
                "indication_norm": "hematology",
                "therapeutic_area": "oncology",
                "trial_phase": "nda",
                "trial_phase_raw": "NDA",
                "route_of_administration": "oral",
                "source_type": "api_test",
                "source_url": "https://codex.test/pipeline/api",
                "evidence_text": "api route pipeline evidence",
                "confidence_score": 0.88,
            }
        ]
    }
    res = client.post("/api/pipeline/upsert-drugs", json=payload)
    assert_true(res.status_code == 200, f"api upsert failed: {res.status_code} {res.text}")
    body = res.json()
    assert_true(body["created"] + body["updated"] >= 1, "api upsert wrote no rows")

    res = client.get("/api/pipeline/drugs", params={"stock_code": STOCK_CODE})
    assert_true(res.status_code == 200, f"api list failed: {res.status_code} {res.text}")
    items = res.json()["items"]
    assert_true(any(item["drug_name"] == DRUG_API for item in items), "api list did not return api drug")

    bad = client.get("/api/pipeline/drugs", params={"stock_code": "abc"})
    assert_true(bad.status_code == 400, f"invalid stock_code should return 400, got {bad.status_code}")
    print_step("API upsert/query/validation checks passed")


def check_import_batch() -> None:
    batch_id = f"pipeline_full_{RUN_ID}_{uuid.uuid4().hex[:8]}"
    batch_dir = BACKEND_ROOT / "data" / "incoming" / batch_id
    pipeline_dir = batch_dir / "pipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "batch_id": batch_id,
        "status": "ready",
        "data_types": ["pipeline_drug"],
        "files": {"pipeline_drug": "pipeline/pipeline_drug_records.jsonl"},
    }
    (batch_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    record = {
        "stock_code": STOCK_CODE,
        "drug_name": DRUG_IMPORT,
        "canonical_drug_name": DRUG_IMPORT,
        "aliases": [f"{DRUG_IMPORT}-alias"],
        "indication": "melanoma",
        "indication_norm": "melanoma",
        "therapeutic_area": "oncology",
        "trial_phase": "phase1_2",
        "trial_phase_raw": "phase1_2",
        "route_of_administration": "injection",
        "source_type": "openclaw_import_test",
        "source_url": "https://codex.test/pipeline/import",
        "evidence_text": "import_batch pipeline evidence",
        "confidence_score": 0.79,
    }
    (pipeline_dir / "pipeline_drug_records.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    ok = process_batch(batch_dir)
    assert_true(ok, "import_batch process_batch returned false")

    container = ServiceContainer.build_default()
    listed = container.pipeline.list_drugs(STOCK_CODE)
    assert_true(listed.success, f"list after import failed: {listed.message}")
    assert_true(any(item["drug_name"] == DRUG_IMPORT for item in listed.data or []), "import_batch drug was not queryable")

    processed_report = BACKEND_ROOT / "data" / "processed" / batch_id / "import_report.json"
    assert_true(processed_report.exists(), "import_batch did not write processed report")
    print_step("import_batch pipeline_drug checks passed")


def check_vector_sync() -> None:
    container = ServiceContainer.build_default()
    result = container.pipeline.rebuild_embeddings(stock_code=STOCK_CODE)
    assert_true(result.success, f"pipeline embedding rebuild failed: {result.message}")
    assert_true((result.data or {}).get("synced_chunks", 0) >= 3, f"expected at least 3 synced chunks, got {result.data}")

    with SessionLocal() as db:
        rows = db.execute(
            select(VectorDocumentIndex)
            .where(VectorDocumentIndex.doc_type == "pipeline_drug")
            .where(VectorDocumentIndex.stock_code == STOCK_CODE)
        ).scalars().all()
        statuses = {row.vector_status for row in rows}
    assert_true(len(rows) >= 3, "vector_document_index has no pipeline entries for test stock")
    assert_true(statuses <= {"success", "fallback_only", "failed"}, f"unexpected vector statuses: {statuses}")
    assert_true("success" in statuses or "fallback_only" in statuses, f"no usable vector status: {statuses}")
    print_step(f"vector sync checks passed: rows={len(rows)}, statuses={sorted(statuses)}")


def check_agent_and_rnpv_run(pipeline_drug_id: int) -> None:
    candidates = list_pipeline_drugs(STOCK_CODE)
    assert_true(candidates, "agent list_pipeline_drugs returned empty list")
    assert_true(candidates[0]["drug_name"] == DRUG_MAIN, f"agent picked wrong first candidate: {candidates[0]}")

    rnpv = calculate_pipeline_rnpv(STOCK_CODE, STOCK_NAME)
    assert_true(rnpv["drug_name"] == DRUG_MAIN, f"rNPV auto-selected wrong drug: {rnpv['drug_name']}")
    assert_true("scenarios" in rnpv and "base" in rnpv["scenarios"], "rNPV result missing scenarios")

    client = TestClient(app)
    run_uid = f"codex-rnpv-{RUN_ID}-{uuid.uuid4().hex[:8]}"
    payload = {
        "run_uid": run_uid,
        "stock_code": STOCK_CODE,
        "pipeline_drug_id": pipeline_drug_id,
        "input_params": {
            "discount_rate": 0.10,
            "horizon_years": 12,
            "scenarios": {
                "bear": {"pos": 0.20, "peak_share": 0.10, "price": 10000, "patient_count": 1000},
                "base": {"pos": 0.45, "peak_share": 0.20, "price": 12000, "patient_count": 1200},
                "bull": {"pos": 0.65, "peak_share": 0.30, "price": 15000, "patient_count": 1500},
            },
        },
        "scenario_results": {
            "bear": {"rnpv_total": 100.0},
            "base": {"rnpv_total": 250.0},
            "bull": {"rnpv_total": 500.0},
        },
        "evidence_refs": [{"source_table": "pipeline_drugs", "source_id": pipeline_drug_id}],
        "warnings": ["test warning"],
        "created_by": "testsql",
    }
    res = client.post("/api/rnpv/runs", json=payload)
    assert_true(res.status_code == 200, f"rNPV run create failed: {res.status_code} {res.text}")
    assert_true(res.json()["run_uid"] == run_uid, "rNPV run response uid mismatch")

    res = client.get("/api/rnpv/runs", params={"stock_code": STOCK_CODE, "limit": 20})
    assert_true(res.status_code == 200, f"rNPV run list failed: {res.status_code} {res.text}")
    assert_true(any(item["run_uid"] == run_uid for item in res.json()["items"]), "created rNPV run not returned by list")

    bad_payload = dict(payload)
    bad_payload["run_uid"] = f"bad-{uuid.uuid4().hex[:8]}"
    bad_payload["input_params"] = {"discount_rate": 2, "horizon_years": 12, "scenarios": {}}
    res = client.post("/api/rnpv/runs", json=bad_payload)
    assert_true(res.status_code == 422, f"invalid rNPV payload should return 422, got {res.status_code}: {res.text}")
    print_step("agent rNPV and rNPV run checks passed")


def check_db_counts() -> None:
    with SessionLocal() as db:
        counts = db.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM pipeline_drugs WHERE stock_code=:stock) AS pipeline_count,
                  (SELECT COUNT(*) FROM rnpv_valuation_runs WHERE stock_code=:stock) AS rnpv_count,
                  (SELECT COUNT(*) FROM vector_document_index WHERE doc_type='pipeline_drug' AND stock_code=:stock) AS vector_count
                """
            ),
            {"stock": STOCK_CODE},
        ).mappings().one()
    assert_true(counts["pipeline_count"] >= 3, f"pipeline_count too small: {dict(counts)}")
    assert_true(counts["rnpv_count"] >= 1, f"rnpv_count too small: {dict(counts)}")
    assert_true(counts["vector_count"] >= 3, f"vector_count too small: {dict(counts)}")
    print_step(f"db counts passed: {dict(counts)}")


def main() -> None:
    print_step(f"using real database with stock_code={STOCK_CODE}, run_id={RUN_ID}")
    check_schema()
    ensure_test_company()
    pipeline_drug_id = check_service_write_query()
    check_api_write_query()
    check_import_batch()
    check_vector_sync()
    check_agent_and_rnpv_run(pipeline_drug_id)
    check_db_counts()
    print_step("ALL PIPELINE TESTS PASSED")


if __name__ == "__main__":
    main()
