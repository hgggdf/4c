"""
ingest_center / run_full_pipeline.py
=====================================

全流程总控脚本。

职责：
    串联四层入库流程：
    1. L1/L2: run_batch（manifest → service 直调）
    2. L3 announcement: run_announcement_l3（staging → service 直调）
    3. L3 news: run_news_l3（staging → service 直调）
    4. L4 maintenance: run_maintenance_l4（按库内数据逐个 rebuild）

    不走 router，不发 HTTP，全部通过 Python 内部函数调用完成。

用法示例：
    python -m ingest_center.run_full_pipeline --dry-run
    python -m ingest_center.run_full_pipeline --skip l3_news,l4
    python -m ingest_center.run_full_pipeline --fail-fast
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Set

from . import common
from . import config
from . import run_batch
from . import run_announcement_l3
from . import run_maintenance_l4
from . import run_news_l3
from .service_runtime import get_container


# ---------------------------------------------------------------------------
# 数据库反查（为 L4 提供参数）
# ---------------------------------------------------------------------------

def _get_distinct_stock_codes() -> List[str]:
    """从 announcement_raw_hot 反查已落库的 stock_code 列表。"""
    try:
        container = get_container()
        with container.ctx.session() as db:
            from app.core.database.models.announcement_hot import AnnouncementRawHot
            rows = db.query(AnnouncementRawHot.stock_code).distinct().all()
            return sorted([r[0] for r in rows if r[0]])
    except Exception as exc:
        print(f"  [WARN] failed to query stock_codes: {exc}")
        return []


def _get_distinct_industry_codes() -> List[str]:
    """从 industry_impact_event_hot 反查已落库的 industry_code 列表。"""
    try:
        container = get_container()
        with container.ctx.session() as db:
            from app.core.database.models.news_hot import IndustryImpactEventHot
            rows = db.query(IndustryImpactEventHot.industry_code).distinct().all()
            return sorted([r[0] for r in rows if r[0]])
    except Exception as exc:
        print(f"  [WARN] failed to query industry_codes: {exc}")
        return []


def _get_announcement_time_params() -> tuple[int, str]:
    """从 announcement_raw_hot 读取最新 publish_date，推断 year 和 year_month。"""
    try:
        container = get_container()
        with container.ctx.session() as db:
            from app.core.database.models.announcement_hot import AnnouncementRawHot
            from sqlalchemy import func
            max_date = db.query(func.max(AnnouncementRawHot.publish_date)).scalar()
            if max_date:
                return max_date.year, max_date.strftime("%Y-%m")
    except Exception as exc:
        print(f"  [WARN] failed to query announcement time params: {exc}")
    return 2026, "2026-03"


def _get_news_time_params() -> str:
    """从 news_raw_hot 读取最新 publish_time，推断 year_month。"""
    try:
        container = get_container()
        with container.ctx.session() as db:
            from app.core.database.models.news_hot import NewsRawHot
            from sqlalchemy import func
            max_time = db.query(func.max(NewsRawHot.publish_time)).scalar()
            if max_time:
                return max_time.strftime("%Y-%m")
    except Exception as exc:
        print(f"  [WARN] failed to query news time params: {exc}")
    return "2026-03"


# ---------------------------------------------------------------------------
# 各层执行
# ---------------------------------------------------------------------------

def _run_l12(manifest_dir: str, dry_run: bool, fail_fast: bool) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("[LAYER 1/2] run_batch")
    print("=" * 70)
    result = run_batch.run(
        manifest_dir=manifest_dir,
        dry_run=dry_run,
        fail_fast=fail_fast,
    )
    return {
        "success": result.get("success", False),
        "details": result.get("details", []),
    }


def _run_l3_announcement(staging_dir: str, dry_run: bool) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("[LAYER 3] announcement")
    print("=" * 70)
    result = run_announcement_l3.run(
        staging_dir=staging_dir,
        category="all",
        dry_run=dry_run,
    )
    return {
        "success": result.get("success", False),
        "receipt_path": result.get("receipt_path"),
        "executed_categories": result.get("executed_categories", []),
        "failed_categories": result.get("failed_categories", []),
    }


def _run_l3_news(staging_dir: str, dry_run: bool) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("[LAYER 3] news")
    print("=" * 70)
    result = run_news_l3.run(
        staging_dir=staging_dir,
        category="all",
        dry_run=dry_run,
    )
    return {
        "success": result.get("success", False),
        "receipt_path": result.get("receipt_path"),
        "executed_categories": result.get("executed_categories", []),
        "failed_categories": result.get("failed_categories", []),
    }


def _run_l4(dry_run: bool) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("[LAYER 4] maintenance")
    print("=" * 70)

    stock_codes = _get_distinct_stock_codes()
    industry_codes = _get_distinct_industry_codes()
    year, year_month = _get_announcement_time_params()
    news_year_month = _get_news_time_params()

    print(f"  stock_codes   : {stock_codes}")
    print(f"  industry_codes: {industry_codes}")
    print(f"  year          : {year}")
    print(f"  year_month    : {year_month}")
    print(f"  news_year_month: {news_year_month}")

    all_executed: List[str] = []
    all_failed: List[Dict[str, Any]] = []

    # stock_code 相关任务
    for sc in stock_codes:
        for task in [
            "announcement_summary_monthly",
            "drug_pipeline_summary_yearly",
            "financial_metric_summary_yearly",
        ]:
            kwargs: Dict[str, Any] = {
                "task": task,
                "stock_code": sc,
                "dry_run": dry_run,
            }
            if task == "announcement_summary_monthly":
                kwargs["year_month"] = year_month
            else:
                kwargs["year"] = year

            print(f"\n[L4-EXEC] {task} stock_code={sc}")
            result = run_maintenance_l4.run(**kwargs)
            all_executed.extend(result.get("executed_tasks", []))
            all_failed.extend(result.get("failed_tasks", []))

    # industry_code 相关任务
    for ic in industry_codes:
        task = "industry_news_summary_monthly"
        print(f"\n[L4-EXEC] {task} industry_code={ic}")
        result = run_maintenance_l4.run(
            task=task,
            industry_code=ic,
            year_month=news_year_month,
            dry_run=dry_run,
        )
        all_executed.extend(result.get("executed_tasks", []))
        all_failed.extend(result.get("failed_tasks", []))

    return {
        "success": len(all_failed) == 0,
        "executed_tasks_count": len(all_executed),
        "failed_tasks_count": len(all_failed),
        "failed_details": all_failed,
    }


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def _build_receipt_path() -> str:
    ts = common.now_iso().replace(":", "").replace("+", "_")
    filename = f"full_pipeline_{ts}.json"
    return os.path.join(config.RECEIPT_DIR, filename)


def _write_receipt(
    *,
    receipt_path: str,
    manifest_dir: str,
    dry_run: bool,
    fail_fast: bool,
    skip: List[str],
    layer_results: Dict[str, Any],
    executed_layers: List[str],
    failed_layers: List[str],
) -> str:
    status = "validated" if dry_run else ("done" if not failed_layers else "failed")
    success = dry_run or (len(failed_layers) == 0 and len(executed_layers) > 0)

    receipt = {
        "job_type": "full_pipeline",
        "manifest_dir": manifest_dir,
        "dry_run": dry_run,
        "fail_fast": fail_fast,
        "skip": skip,
        "layer_results": layer_results,
        "executed_layers": executed_layers,
        "failed_layers": failed_layers,
        "status": status,
        "success": success,
        "created_at": common.now_iso(),
    }

    common.write_receipt(receipt_path, receipt)
    return receipt_path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(
    manifest_dir: str,
    dry_run: bool = False,
    fail_fast: bool = False,
    skip: Optional[List[str]] = None,
    staging_dir: Optional[str] = None,
) -> None:
    """
    执行全流程总控。

    Args:
        manifest_dir: manifest 扫描目录。
        dry_run: 为 True 时各层以 dry-run 模式执行。
        fail_fast: 为 True 时某层失败立即停止后续层。
        skip: 要跳过的层列表，如 ["l3_news", "l4"]。
        staging_dir: L3 staging 目录。默认为 crawler/staging/e2e。
    """
    skip_set: Set[str] = set(skip or [])
    if staging_dir is None:
        staging_dir = os.path.join(config.PROJECT_ROOT, "crawler", "staging", "e2e")

    print("=" * 70)
    print("FULL PIPELINE")
    print("=" * 70)
    print(f"manifest_dir : {manifest_dir}")
    print(f"dry_run      : {dry_run}")
    print(f"fail_fast    : {fail_fast}")
    print(f"skip         : {sorted(skip_set)}")
    print("=" * 70)

    layer_results: Dict[str, Any] = {}
    executed_layers: List[str] = []
    failed_layers: List[str] = []

    # 1. L1/L2
    if "l12" not in skip_set:
        result = _run_l12(manifest_dir, dry_run, fail_fast)
        layer_results["l12"] = result
        if result["success"]:
            executed_layers.append("l12")
        else:
            failed_layers.append("l12")
            if fail_fast:
                print("\n[FAIL-FAST] L1/L2 failed, aborting pipeline.")
    else:
        layer_results["l12"] = {"success": True, "skipped": True}
        print("\n[SKIP] L1/L2")

    # 2. L3 announcement
    if "l3_announcement" not in skip_set and (not fail_fast or not failed_layers):
        result = _run_l3_announcement(staging_dir, dry_run)
        layer_results["l3_announcement"] = result
        if result["success"]:
            executed_layers.append("l3_announcement")
        else:
            failed_layers.append("l3_announcement")
            if fail_fast:
                print("\n[FAIL-FAST] L3 announcement failed, aborting pipeline.")
    else:
        layer_results["l3_announcement"] = {"success": True, "skipped": True}
        if "l3_announcement" in skip_set:
            print("\n[SKIP] L3 announcement")

    # 3. L3 news
    if "l3_news" not in skip_set and (not fail_fast or not failed_layers):
        result = _run_l3_news(staging_dir, dry_run)
        layer_results["l3_news"] = result
        if result["success"]:
            executed_layers.append("l3_news")
        else:
            failed_layers.append("l3_news")
            if fail_fast:
                print("\n[FAIL-FAST] L3 news failed, aborting pipeline.")
    else:
        layer_results["l3_news"] = {"success": True, "skipped": True}
        if "l3_news" in skip_set:
            print("\n[SKIP] L3 news")

    # 4. L4 maintenance
    if "l4" not in skip_set and (not fail_fast or not failed_layers):
        result = _run_l4(dry_run)
        layer_results["l4"] = result
        if result["success"]:
            executed_layers.append("l4")
        else:
            failed_layers.append("l4")
            if fail_fast:
                print("\n[FAIL-FAST] L4 failed, aborting pipeline.")
    else:
        layer_results["l4"] = {"success": True, "skipped": True}
        if "l4" in skip_set:
            print("\n[SKIP] L4")

    # 总 receipt
    receipt_path = _build_receipt_path()
    _write_receipt(
        receipt_path=receipt_path,
        manifest_dir=manifest_dir,
        dry_run=dry_run,
        fail_fast=fail_fast,
        skip=sorted(skip_set),
        layer_results=layer_results,
        executed_layers=executed_layers,
        failed_layers=failed_layers,
    )

    # 控制台 summary
    print("\n" + "=" * 70)
    print("FULL PIPELINE SUMMARY")
    print("=" * 70)
    for layer in ["l12", "l3_announcement", "l3_news", "l4"]:
        res = layer_results.get(layer, {})
        if res.get("skipped"):
            status = "skipped"
        elif layer in failed_layers:
            status = "failed"
        elif layer in executed_layers:
            status = "done"
        else:
            status = "unknown"
        print(f"  {layer:18s}: {status}")
    print(f"executed_layers : {executed_layers}")
    print(f"failed_layers   : {failed_layers}")
    print(f"receipt_path    : {receipt_path}")
    print("=" * 70)

    if failed_layers:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full pipeline orchestrator. Runs L1/L2 → L3 → L4 sequentially."
    )
    parser.add_argument(
        "--manifest-dir",
        default=os.path.join(config.PROJECT_ROOT, "ingest_center", "manifests_e2e"),
        help="Directory containing manifest JSON files to ingest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all layers in dry-run mode.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first layer failure.",
    )
    parser.add_argument(
        "--skip",
        default="",
        help='Comma-separated list of layers to skip: l12, l3_announcement, l3_news, l4',
    )
    parser.add_argument(
        "--staging-dir",
        default=None,
        help="Directory containing L3 staging files. Defaults to crawler/staging/e2e.",
    )
    args = parser.parse_args()

    skip = [s.strip() for s in args.skip.split(",") if s.strip()]
    valid_skips = {"l12", "l3_announcement", "l3_news", "l4"}
    invalid = [s for s in skip if s not in valid_skips]
    if invalid:
        print(f"[ERROR] invalid --skip values: {invalid}. Valid: {sorted(valid_skips)}")
        sys.exit(1)

    run(
        manifest_dir=args.manifest_dir,
        dry_run=args.dry_run,
        fail_fast=args.fail_fast,
        skip=skip,
        staging_dir=args.staging_dir,
    )


if __name__ == "__main__":
    main()
