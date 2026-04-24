#!/usr/bin/env python3
"""
run_market.py
stock_daily 链入库脚本

读取 staging/stock_daily_package.json
调用 POST /api/ingest/financial-package
只写入 stock_daily 字段，其他字段为空数组
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest_jobs import (
    get_config,
    HttpClient,
    ManifestLoader,
    StagingLoader,
    IngestJobBuilder,
    validate_manifest,
    validate_staging,
)


def run_market(job_id: str | None = None, dry_run: bool = False) -> dict:
    """
    执行 stock_daily 入库

    流程：
    1. 按 job_id 加载 manifest（或最新 ready 的 manifest）
    2. 校验 manifest + staging
    3. 调用 /api/ingest/financial-package
    4. 更新 manifest status
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
        manifest = next((m for m in manifests if m.data_category == "stock_daily"), None)

    if manifest is None:
        return {"success": False, "error": "未找到 stock_daily manifest"}

    # 2. 校验
    validation = validate_manifest(manifest.raw_manifest)
    if not validation.is_valid:
        return {"success": False, "errors": validation.errors}

    staging_data = staging_loader.load_for_manifest(manifest)
    if staging_data is None:
        return {"success": False, "error": "staging 文件加载失败"}

    staging_validation = validate_staging(staging_data, "stock_daily")
    if not staging_validation.is_valid:
        return {"success": False, "errors": staging_validation.errors}

    payload = staging_data.get("payload", {})
    records = payload.get("stock_daily", [])

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "job_id": manifest.job_id,
            "data_category": "stock_daily",
            "staging_count": len(records),
            "endpoint": manifest.target_endpoint,
        }

    # 3. 调用 API
    api_payload = {
        "income_statements": [],
        "balance_sheets": [],
        "cashflow_statements": [],
        "financial_metrics": [],
        "financial_notes": [],
        "business_segments": [],
        "stock_daily": records,
        "sync_vector_index": False,
    }

    response = http.post(manifest.target_endpoint, api_payload)

    # 4. 更新 manifest status
    updated_manifest = dict(manifest.raw_manifest)
    updated_manifest["status"] = "done" if response.is_success else "failed"
    if response.is_success:
        manifest_path = Path(config.manifests_dir) / f"{manifest.job_id}.json"
        manifest_path.write_text(__import__("json").dumps(updated_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": response.is_success,
        "job_id": manifest.job_id,
        "data_category": "stock_daily",
        "endpoint": manifest.target_endpoint,
        "status_code": response.status_code,
        "written_count": len(records),
        "error": response.error,
        "elapsed_ms": response.elapsed_ms,
    }


def main():
    parser = argparse.ArgumentParser(description="stock_daily 入库脚本")
    parser.add_argument("--job-id", dest="job_id", default=None, help="指定 job_id")
    parser.add_argument("--dry-run", action="store_true", help="只校验不写入")
    parser.add_argument("--backend", dest="backend_root", default=None, help="backend 根目录")

    args = parser.parse_args()
    if args.backend_root:
        import ingest_jobs.config as _cfg
        _cfg._config = None  # 重置单例

    result = run_market(job_id=args.job_id, dry_run=args.dry_run)
    print(__import__("json").dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
