#!/usr/bin/env python3
"""
run_report.py
research_report 链入库脚本

读取 staging/research_reports_phasec_live/research_reports_latest.json
调用 POST /api/ingest/news-package
只写入 news_raw 字段
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest_jobs import (
    get_config,
    HttpClient,
    ManifestLoader,
    StagingLoader,
    validate_manifest,
    validate_staging,
)


def run_report(job_id: str | None = None, dry_run: bool = False) -> dict:
    """
    执行 research_report 入库
    """
    config = get_config()
    http = HttpClient()
    manifest_loader = ManifestLoader()
    staging_loader = StagingLoader()

    # 1. 加载 manifest
    if job_id:
        manifest = manifest_loader.load(job_id)
    else:
        manifests = manifest_loader.list_pending_manifests()
        manifest = next((m for m in manifests if m.data_category == "research_report"), None)

    if manifest is None:
        return {"success": False, "error": "未找到 research_report manifest"}

    # 2. 校验
    validation = validate_manifest(manifest.raw_manifest)
    if not validation.is_valid:
        return {"success": False, "errors": validation.errors}

    staging_data = staging_loader.load_for_manifest(manifest)
    if staging_data is None:
        return {"success": False, "error": "staging 文件加载失败"}

    staging_validation = validate_staging(staging_data, "research_report")
    if not staging_validation.is_valid:
        return {"success": False, "errors": staging_validation.errors}

    payload = staging_data.get("payload", {})
    records = payload.get("news_raw", [])

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "job_id": manifest.job_id,
            "data_category": "research_report",
            "staging_count": len(records),
            "endpoint": manifest.target_endpoint,
        }

    # 3. 调用 API
    api_payload = {
        "macro_indicators": [],
        "news_raw": records,
        "news_structured": [],
        "news_industry_maps": {},
        "news_company_maps": {},
        "industry_impact_events": [],
        "sync_vector_index": True,
    }

    response = http.post(manifest.target_endpoint, api_payload)

    # 4. 更新 manifest status
    if response.is_success:
        updated_manifest = dict(manifest.raw_manifest)
        updated_manifest["status"] = "done"
        manifest_path = Path(config.manifests_dir) / f"{manifest.job_id}.json"
        manifest_path.write_text(json.dumps(updated_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": response.is_success,
        "job_id": manifest.job_id,
        "data_category": "research_report",
        "endpoint": manifest.target_endpoint,
        "status_code": response.status_code,
        "written_count": len(records),
        "error": response.error,
        "elapsed_ms": response.elapsed_ms,
    }


def main():
    parser = argparse.ArgumentParser(description="research_report 入库脚本")
    parser.add_argument("--job-id", dest="job_id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backend", dest="backend_root", default=None)

    args = parser.parse_args()
    if args.backend_root:
        import ingest_jobs.config as _cfg
        _cfg._config = None

    result = run_report(job_id=args.job_id, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
