"""
ingest_center / run_batch.py
===========================

批量任务入库入口模块。

职责：
    扫描 manifests/ 目录下的全部待处理 manifest，按固定顺序逐个调用 run_one.run() 执行入库，
    并汇总生成批量执行报告。

用法示例：
    python -m ingest_center.run_batch --dry-run
    python -m ingest_center.run_batch
    python -m ingest_center.run_batch --category stock_daily
    python -m ingest_center.run_batch --job-id example_stock_daily_001
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import config
from . import manifest_model
from . import run_one


# data_category 固定执行顺序
CATEGORY_ORDER = [
    "company",
    "stock_daily",
    "announcement_raw",
    "research_report",
    "macro",
    "patent",
]


def _category_sort_key(item: Dict[str, Any]) -> int:
    """返回 data_category 在固定顺序中的索引，未知类别排最后。"""
    try:
        return CATEGORY_ORDER.index(item["data_category"])
    except ValueError:
        return len(CATEGORY_ORDER)


def _parse_manifest_safe(path: str) -> Optional[Dict[str, Any]]:
    """
    安全解析 manifest，失败时返回 None。

    Returns:
        包含 path / data_category / status / job_id 的字典，或 None。
    """
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
    收集指定目录下所有可解析且 status == "ready" 的 manifest。

    Args:
        manifest_dir: manifest 扫描目录。

    Returns:
        manifest 信息列表，已按 CATEGORY_ORDER 排序。
    """
    if not os.path.isdir(manifest_dir):
        return []

    manifests: List[Dict[str, Any]] = []
    for entry in os.listdir(manifest_dir):
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

        manifests.append(parsed)

    manifests.sort(key=_category_sort_key)
    return manifests


def _print_summary(results: List[Dict[str, Any]]) -> None:
    """打印批量执行汇总报告。"""
    total = len(results)
    done_count = sum(1 for r in results if r["result"] == "done")
    failed_count = sum(1 for r in results if r["result"] == "failed")
    skipped_count = sum(1 for r in results if r["result"] == "skipped")
    validated_count = sum(1 for r in results if r["result"] == "validated")

    # per-category 统计
    per_category: Dict[str, Dict[str, int]] = {}
    for cat in CATEGORY_ORDER:
        per_category[cat] = {"done": 0, "failed": 0, "skipped": 0, "validated": 0, "total": 0}
    for r in results:
        cat = r.get("data_category", "unknown")
        if cat not in per_category:
            per_category[cat] = {"done": 0, "failed": 0, "skipped": 0, "validated": 0, "total": 0}
        per_category[cat]["total"] += 1
        per_category[cat][r["result"]] += 1

    print("\n" + "=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"total_manifests : {total}")
    print(f"done_count      : {done_count}")
    print(f"failed_count    : {failed_count}")
    print(f"skipped_count   : {skipped_count}")
    print(f"validated_count : {validated_count}")
    print("-" * 60)
    print("per_category:")
    for cat in CATEGORY_ORDER:
        stats = per_category.get(cat, {"done": 0, "failed": 0, "skipped": 0, "validated": 0, "total": 0})
        print(f"  {cat:<20} total={stats['total']} done={stats['done']} failed={stats['failed']} skipped={stats['skipped']} validated={stats['validated']}")
    print("=" * 60)


def run(
    manifest_dir: str,
    dry_run: bool = False,
    category: Optional[str] = None,
    job_id: Optional[str] = None,
    fail_fast: bool = False,
) -> None:
    """
    执行批量入库主流程。

    Args:
        manifest_dir: manifest 扫描目录。
        dry_run: 为 True 时不调用 service，仅执行本地校验。
        category: 若指定，只处理该 data_category。
        job_id: 若指定，只处理该 job_id（精确匹配）。
        fail_fast: 为 True 时首个失败后立即退出。
    """
    manifests = collect_manifest_paths(manifest_dir)

    # 按 category 过滤
    if category is not None:
        manifests = [m for m in manifests if m["data_category"] == category]

    # 按 job_id 过滤
    if job_id is not None:
        manifests = [m for m in manifests if m["job_id"] == job_id]

    if not manifests:
        print("[INFO] no ready manifests to process.")
        return

    results: List[Dict[str, Any]] = []

    for manifest_info in manifests:
        path = manifest_info["path"]
        cat = manifest_info["data_category"]
        jid = manifest_info["job_id"]
        print(f"\n[PROCESS] {jid} ({cat}) -> {path}")

        try:
            run_one.run(path, dry_run=dry_run)
            # run_one.run 成功时直接 return，无返回值
            # 需要根据 receipt 文件反推真实状态（done / validated / skipped）
            receipt_path = os.path.join(config.RECEIPT_DIR, f"{jid}.json")
            result_status = "done"
            if os.path.isfile(receipt_path):
                try:
                    with open(receipt_path, "r", encoding="utf-8") as f:
                        receipt = json.load(f)
                    result_status = receipt.get("status", "done")
                except Exception:
                    pass
            results.append({
                "job_id": jid,
                "data_category": cat,
                "result": result_status,
            })
        except SystemExit as exc:
            # run_one.run 失败时会 sys.exit(1)
            results.append({
                "job_id": jid,
                "data_category": cat,
                "result": "failed",
            })
            if fail_fast:
                print(f"[FAIL-FAST] {jid} failed, aborting batch.")
                break
        except Exception as exc:
            results.append({
                "job_id": jid,
                "data_category": cat,
                "result": "failed",
            })
            print(f"[FAIL] {jid} unexpected error: {exc}")
            if fail_fast:
                print(f"[FAIL-FAST] {jid} failed, aborting batch.")
                break

    _print_summary(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ingest manifests into the backend.")
    parser.add_argument(
        "--manifest-dir",
        default=config.MANIFEST_DIR,
        help="Directory containing manifest JSON files to ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all local validations without calling service.",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Process only manifests of this data_category.",
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
    run(
        manifest_dir=args.manifest_dir,
        dry_run=args.dry_run,
        category=args.category,
        job_id=args.job_id,
        fail_fast=args.fail_fast,
    )


if __name__ == "__main__":
    main()
