"""
ingest_center / run_financial_batch.py
======================================

Financial package 批量入库入口模块。

职责：
    扫描 manifests_financial/ 目录下的全部 financial_package manifest，
    逐个执行本地校验、payload 构造、直接调用 container.ingest.ingest_financial_package
    完成 6 张财务表的批量写入。

    不走 HTTP，直接通过 ServiceContainer 内部调用。

用法示例：
    python -m ingest_center.run_financial_batch --dry-run
    python -m ingest_center.run_financial_batch --manifest-dir ingest_center/manifests_financial
    python -m ingest_center.run_financial_batch --job-id financial_600000_2025-12-31_年报
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.service.write_requests import IngestFinancialPackageRequest

from . import common
from . import config
from . import file_checks
from . import manifest_model
from . import payload_builder
from .service_runtime import get_container


# config.PROJECT_ROOT 指向 backend/，真正的项目根目录是其上级
_PROJECT_ROOT = os.path.dirname(config.PROJECT_ROOT)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """返回当前 UTC ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(path: str) -> str:
    """
    解析 manifest 中的文件路径。

    规则：
        - 绝对路径直接使用
        - 相对路径以项目根目录为基准解析
    """
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(_PROJECT_ROOT, path))


def _extract_written_count(response_data: Optional[Any]) -> Optional[int]:
    """
    从 service 返回数据中尽可能提取写入计数。

    对 financial_package 的多表返回结构做累加：
        {"income_statements": {"total": 1, ...}, "balance_sheets": {"total": 2, ...}, ...}
    """
    if response_data is None:
        return None

    if isinstance(response_data, dict):
        # financial_package 多表结果：累加各表 total
        financial_keys = (
            "income_statements",
            "balance_sheets",
            "cashflow_statements",
            "financial_metrics",
            "financial_notes",
            "business_segments",
        )
        if any(k in response_data for k in financial_keys):
            total = 0
            for key in financial_keys:
                val = response_data.get(key)
                if isinstance(val, dict):
                    total += val.get("total", 0)
            return total if total > 0 else None

        # 单表通用查找
        for key in ("total", "count", "written_count", "created_count"):
            val = response_data.get(key)
            if isinstance(val, int):
                return val

    return None


def _build_receipt(
    *,
    job_id: str,
    manifest_path: str,
    staging_path: str,
    endpoint: Optional[str],
    status: str,
    success: bool,
    error_message: Optional[str],
    error_code: Optional[str],
    response_data: Optional[Any],
    dry_run: bool,
) -> Dict[str, Any]:
    """构造 receipt 字典。"""
    return {
        "job_id": job_id,
        "data_category": "financial_package",
        "manifest_path": manifest_path,
        "staging_path": staging_path,
        "endpoint": endpoint,
        "status": status,
        "success": success,
        "written_count": None if dry_run else _extract_written_count(response_data),
        "error_code": error_code,
        "error_message": error_message,
        "trace_id": None,
        "warnings": None,
        "created_at": _now_iso(),
    }


def _write_receipt(receipt: Dict[str, Any], job_id: str) -> str:
    """将 receipt 写入 receipts 目录。"""
    os.makedirs(config.RECEIPT_DIR, exist_ok=True)
    receipt_path = os.path.join(config.RECEIPT_DIR, f"{job_id}.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    return receipt_path


# ---------------------------------------------------------------------------
# Manifest 收集
# ---------------------------------------------------------------------------

def _parse_manifest_safe(path: str) -> Optional[Dict[str, Any]]:
    """安全解析 manifest，失败时返回 None。"""
    try:
        manifest_obj = manifest_model.parse_manifest(path)
        return {
            "path": path,
            "job_id": manifest_obj.job_id,
            "data_category": manifest_obj.data_category,
            "status": manifest_obj.status,
        }
    except Exception:
        return None


def collect_manifest_paths(manifest_dir: str) -> List[Dict[str, Any]]:
    """
    收集指定目录下所有可解析且 status == "ready" 的 financial_package manifest。

    Returns:
        manifest 信息列表，已按文件名排序。
    """
    if not os.path.isdir(manifest_dir):
        return []

    manifests: List[Dict[str, Any]] = []
    for entry in sorted(os.listdir(manifest_dir)):
        if not entry.endswith(".json"):
            continue
        path = os.path.join(manifest_dir, entry)
        if not os.path.isfile(path):
            continue

        parsed = _parse_manifest_safe(path)
        if parsed is None:
            continue
        if parsed["status"] != "ready":
            continue
        if parsed["data_category"] != "financial_package":
            continue

        manifests.append(parsed)

    return manifests


# ---------------------------------------------------------------------------
# 单任务执行
# ---------------------------------------------------------------------------

def _run_one(manifest_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    执行单个 financial_package manifest 的入库流程。

    Returns:
        {"success": bool, "status": str, "job_id": str, ...}
    """
    # 1. 解析 manifest
    manifest_obj = manifest_model.parse_manifest(manifest_path)
    job_id = manifest_obj.job_id
    data_category = manifest_obj.data_category
    endpoint = manifest_obj.target.endpoint

    # 2. data_category 校验
    if data_category != "financial_package":
        raise ValueError(
            f"expected data_category='financial_package', got {data_category!r}"
        )

    # 3. 解析 staging 路径
    staging_path = _resolve_path(manifest_obj.files.staging_path)

    # 4. 校验 staging 文件存在
    try:
        file_checks.ensure_file_exists(staging_path)
    except FileNotFoundError as exc:
        receipt = _build_receipt(
            job_id=job_id,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=endpoint,
            status="failed",
            success=False,
            error_message=str(exc),
            error_code="FILE_NOT_FOUND",
            response_data=None,
            dry_run=dry_run,
        )
        _write_receipt(receipt, job_id)
        print(f"  [FAIL] {exc}")
        return {"success": False, "status": "failed", "job_id": job_id, "error": str(exc)}

    # 5. 校验 staging sha256
    try:
        file_checks.verify_sha256(staging_path, manifest_obj.checksum.staging_sha256)
    except ValueError as exc:
        receipt = _build_receipt(
            job_id=job_id,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=endpoint,
            status="failed",
            success=False,
            error_message=str(exc),
            error_code="CHECKSUM_MISMATCH",
            response_data=None,
            dry_run=dry_run,
        )
        _write_receipt(receipt, job_id)
        print(f"  [FAIL] {exc}")
        return {"success": False, "status": "failed", "job_id": job_id, "error": str(exc)}

    # 6. 加载 staging
    with open(staging_path, "r", encoding="utf-8") as f:
        staging = json.load(f)

    # 7. 构造 payload
    payload = payload_builder.build_payload(data_category, staging)

    # 8. 统计各类数组数量
    counts = {
        "income_statements": len(payload.get("income_statements", [])),
        "balance_sheets": len(payload.get("balance_sheets", [])),
        "cashflow_statements": len(payload.get("cashflow_statements", [])),
        "financial_metrics": len(payload.get("financial_metrics", [])),
        "financial_notes": len(payload.get("financial_notes", [])),
        "business_segments": len(payload.get("business_segments", [])),
    }
    total_count = sum(counts.values())

    # 9. dry-run 分支
    if dry_run:
        print(f"  [DRY-RUN] counts={counts}, total={total_count}")
        receipt = _build_receipt(
            job_id=job_id,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=endpoint,
            status="validated",
            success=True,
            error_message=None,
            error_code=None,
            response_data={"counts": counts, "total": total_count},
            dry_run=True,
        )
        receipt_path = _write_receipt(receipt, job_id)
        print(f"  [VALIDATED] receipt: {receipt_path}")
        return {
            "success": True,
            "status": "validated",
            "job_id": job_id,
            "counts": counts,
            "total": total_count,
        }

    # 10. 真实执行：直接调用 container.ingest.ingest_financial_package
    print(f"  [EXECUTE] counts={counts}, total={total_count}")
    container = get_container()
    req = IngestFinancialPackageRequest(**payload)

    try:
        result = container.ingest.ingest_financial_package(req)
    except Exception as exc:
        # 捕获 service 层抛出的非 ServiceResult 异常
        err_msg = f"[{type(exc).__name__}] {exc}"
        print(f"  [FAIL] {err_msg}")
        receipt = _build_receipt(
            job_id=job_id,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=endpoint,
            status="failed",
            success=False,
            error_message=err_msg,
            error_code="INTERNAL_ERROR",
            response_data=None,
            dry_run=False,
        )
        _write_receipt(receipt, job_id)
        return {"success": False, "status": "failed", "job_id": job_id, "error": err_msg}

    if not result.success:
        print(f"  [FAIL] {result.message} ({result.error_code})")
        receipt = _build_receipt(
            job_id=job_id,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=endpoint,
            status="failed",
            success=False,
            error_message=result.message,
            error_code=result.error_code,
            response_data=result.data,
            dry_run=False,
        )
        _write_receipt(receipt, job_id)
        return {
            "success": False,
            "status": "failed",
            "job_id": job_id,
            "error": f"{result.message} ({result.error_code})",
        }

    # 成功
    written_count = _extract_written_count(result.data)
    print(f"  [DONE] written_count={written_count}")
    receipt = _build_receipt(
        job_id=job_id,
        manifest_path=manifest_path,
        staging_path=staging_path,
        endpoint=endpoint,
        status="done",
        success=True,
        error_message=None,
        error_code=None,
        response_data=result.data,
        dry_run=False,
    )
    _write_receipt(receipt, job_id)
    return {
        "success": True,
        "status": "done",
        "job_id": job_id,
        "counts": counts,
        "written_count": written_count,
        "details": result.data,
    }


# ---------------------------------------------------------------------------
# 批量执行与 Summary
# ---------------------------------------------------------------------------

def _print_summary(results: List[Dict[str, Any]]) -> None:
    """打印批量执行汇总报告。"""
    total = len(results)
    done_count = sum(1 for r in results if r.get("status") == "done")
    failed_count = sum(1 for r in results if r.get("status") == "failed")
    validated_count = sum(1 for r in results if r.get("status") == "validated")

    print("\n" + "=" * 60)
    print("FINANCIAL BATCH SUMMARY")
    print("=" * 60)
    print(f"total_manifests : {total}")
    print(f"done_count      : {done_count}")
    print(f"failed_count    : {failed_count}")
    print(f"validated_count : {validated_count}")
    print("=" * 60)

    if failed_count > 0:
        print("failed details:")
        for r in results:
            if r.get("status") == "failed":
                print(f"  - {r.get('job_id')}: {r.get('error')}")
        print("=" * 60)


def run(
    manifest_dir: str,
    dry_run: bool = False,
    job_id: Optional[str] = None,
    fail_fast: bool = False,
) -> Dict[str, Any]:
    """
    执行 financial_package 批量入库主流程。

    Args:
        manifest_dir: manifest 扫描目录。
        dry_run: 为 True 时不调用 service，仅执行本地校验与 payload 构造。
        job_id: 若指定，只处理该 job_id（精确匹配）。
        fail_fast: 为 True 时首个失败后立即退出。

    Returns:
        {"success": bool, "details": [...]}
    """
    manifests = collect_manifest_paths(manifest_dir)

    # 按 job_id 过滤
    if job_id is not None:
        manifests = [m for m in manifests if m["job_id"] == job_id]

    if not manifests:
        print("[INFO] no ready financial_package manifests to process.")
        return {"success": True, "details": []}

    results: List[Dict[str, Any]] = []

    for manifest_info in manifests:
        path = manifest_info["path"]
        jid = manifest_info["job_id"]
        print(f"\n[PROCESS] {jid} -> {path}")

        try:
            outcome = _run_one(path, dry_run=dry_run)
            results.append(outcome)
            if not outcome["success"] and fail_fast:
                print(f"[FAIL-FAST] {jid} failed, aborting batch.")
                break
        except SystemExit:
            results.append({"success": False, "status": "failed", "job_id": jid, "error": "SystemExit"})
            if fail_fast:
                print(f"[FAIL-FAST] {jid} failed, aborting batch.")
                break
        except Exception as exc:
            results.append({"success": False, "status": "failed", "job_id": jid, "error": str(exc)})
            print(f"[FAIL] {jid} unexpected error: {exc}")
            if fail_fast:
                print(f"[FAIL-FAST] {jid} failed, aborting batch.")
                break

    _print_summary(results)

    failed_count = sum(1 for r in results if not r.get("success", False))
    return {"success": failed_count == 0, "details": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch ingest financial_package manifests into the backend."
    )
    parser.add_argument(
        "--manifest-dir",
        default=os.path.join(config.PROJECT_ROOT, "ingest_center", "manifests_financial"),
        help="Directory containing financial_package manifest JSON files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all local validations without calling service.",
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="Process only the manifest with this job_id.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first failure instead of continuing.",
    )
    args = parser.parse_args()

    result = run(
        manifest_dir=args.manifest_dir,
        dry_run=args.dry_run,
        job_id=args.job_id,
        fail_fast=args.fail_fast,
    )

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
