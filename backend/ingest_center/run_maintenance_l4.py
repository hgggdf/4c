"""
ingest_center / run_maintenance_l4.py
====================================

第4层汇总 job。

职责：
    直调 MaintenanceService 的 rebuild 方法，执行汇总/聚合任务。
    不走 router，不走 HTTP，完全通过 ServiceContainer 内部调用。

涵盖任务：
    - announcement_summary_monthly    → rebuild_announcement_summary_monthly
    - drug_pipeline_summary_yearly    → rebuild_drug_pipeline_summary_yearly
    - financial_metric_summary_yearly → rebuild_financial_metric_summary_yearly
    - industry_news_summary_monthly   → rebuild_industry_news_summary_monthly

用法示例：
    python -m ingest_center.run_maintenance_l4 --task announcement_summary_monthly --stock-code 600276 --year-month 2026-03
    python -m ingest_center.run_maintenance_l4 --task drug_pipeline_summary_yearly --stock-code 600276 --year 2026
    python -m ingest_center.run_maintenance_l4 --task all --stock-code 600276 --year 2026 --year-month 2026-03
    python -m ingest_center.run_maintenance_l4 --task all --dry-run --stock-code 600276 --year 2026
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

from app.service.write_requests import (
    RebuildAnnouncementSummaryRequest,
    RebuildDrugPipelineSummaryRequest,
    RebuildFinancialMetricSummaryRequest,
    RebuildIndustryNewsSummaryRequest,
)

from . import common
from . import config
from .service_runtime import get_container


# ---------------------------------------------------------------------------
# 任务定义
# ---------------------------------------------------------------------------

TASK_REQUIREMENTS: Dict[str, List[str]] = {
    "announcement_summary_monthly": ["stock_code", "year_month"],
    "drug_pipeline_summary_yearly": ["stock_code", "year"],
    "financial_metric_summary_yearly": ["stock_code", "year"],
    "industry_news_summary_monthly": ["industry_code", "year_month"],
}


def _validate_task_params(task: str, args: argparse.Namespace) -> Optional[str]:
    """
    校验指定 task 所需的参数是否齐全。

    Returns:
        若校验通过返回 None，否则返回错误描述字符串。
    """
    required = TASK_REQUIREMENTS.get(task)
    if required is None:
        return f"unknown task: {task}"

    missing = []
    for param in required:
        value = getattr(args, param.replace("-", "_"))
        if value is None or str(value).strip() == "":
            missing.append(f"--{param}")

    if missing:
        return f"task '{task}' missing required params: {', '.join(missing)}"

    return None


def _build_receipt_path(task: str) -> str:
    """生成 receipt 文件路径。"""
    ts = common.now_iso().replace(":", "").replace("+", "_")
    filename = f"maintenance_l4_{task}_{ts}.json"
    return os.path.join(config.RECEIPT_DIR, filename)


def _write_receipt(
    *,
    receipt_path: str,
    task: str,
    stock_code: Optional[str],
    year: Optional[int],
    year_month: Optional[str],
    industry_code: Optional[str],
    dry_run: bool,
    executed_tasks: List[str],
    failed_tasks: List[Dict[str, Any]],
    results: Dict[str, Any],
) -> str:
    """构造并写入 receipt 文件。"""
    status = "validated" if dry_run else ("done" if not failed_tasks else "failed")
    success = dry_run or (len(failed_tasks) == 0 and len(executed_tasks) > 0)

    receipt = {
        "job_type": "maintenance_l4",
        "task": task,
        "stock_code": stock_code,
        "year": year,
        "year_month": year_month,
        "industry_code": industry_code,
        "dry_run": dry_run,
        "status": status,
        "success": success,
        "executed_tasks": executed_tasks,
        "failed_tasks": failed_tasks,
        "results": results,
        "created_at": common.now_iso(),
    }

    common.write_receipt(receipt_path, receipt)
    return receipt_path


# ---------------------------------------------------------------------------
# 任务执行
# ---------------------------------------------------------------------------

def _run_single_task(
    task_name: str,
    *,
    stock_code: Optional[str],
    year: Optional[int],
    year_month: Optional[str],
    industry_code: Optional[str],
    dry_run: bool,
) -> Dict[str, Any]:
    """
    执行单个 maintenance 任务。

    Returns:
        {"success": bool, "task": str, "data": ..., "error": ...}
    """
    container = get_container()

    if dry_run:
        print(f"  [DRY-RUN] would execute: {task_name}")
        return {"success": True, "task": task_name, "data": None, "error": None}

    try:
        if task_name == "announcement_summary_monthly":
            req = RebuildAnnouncementSummaryRequest(
                stock_code=stock_code, year_month=year_month
            )
            result = container.maintenance.rebuild_announcement_summary_monthly(req)

        elif task_name == "drug_pipeline_summary_yearly":
            req = RebuildDrugPipelineSummaryRequest(
                stock_code=stock_code, year=year
            )
            result = container.maintenance.rebuild_drug_pipeline_summary_yearly(req)

        elif task_name == "financial_metric_summary_yearly":
            req = RebuildFinancialMetricSummaryRequest(
                stock_code=stock_code, year=year
            )
            result = container.maintenance.rebuild_financial_metric_summary_yearly(req)

        elif task_name == "industry_news_summary_monthly":
            req = RebuildIndustryNewsSummaryRequest(
                industry_code=industry_code, year_month=year_month
            )
            result = container.maintenance.rebuild_industry_news_summary_monthly(req)

        else:
            return {
                "success": False,
                "task": task_name,
                "data": None,
                "error": f"unknown task: {task_name}",
            }

        if result.success:
            print(f"  [DONE] {task_name}: {result.data}")
            return {"success": True, "task": task_name, "data": result.data, "error": None}
        else:
            print(f"  [FAIL] {task_name}: {result.message} ({result.error_code})")
            return {
                "success": False,
                "task": task_name,
                "data": result.data,
                "error": f"{result.message} ({result.error_code})",
            }

    except Exception as exc:
        print(f"  [FAIL] {task_name}: {exc}")
        return {"success": False, "task": task_name, "data": None, "error": str(exc)}


def _resolve_tasks_for_all(
    args: argparse.Namespace,
) -> List[str]:
    """
    当 task=all 时，根据已提供的参数决定执行哪些子任务。
    """
    tasks: List[str] = []

    # announcement_summary_monthly: stock_code + year_month
    if args.stock_code and args.year_month:
        tasks.append("announcement_summary_monthly")

    # drug_pipeline_summary_yearly: stock_code + year
    if args.stock_code and args.year is not None:
        tasks.append("drug_pipeline_summary_yearly")

    # financial_metric_summary_yearly: stock_code + year
    if args.stock_code and args.year is not None:
        tasks.append("financial_metric_summary_yearly")

    # industry_news_summary_monthly: industry_code + year_month
    if args.industry_code and args.year_month:
        tasks.append("industry_news_summary_monthly")

    return tasks


# ---------------------------------------------------------------------------
# 可复用执行入口
# ---------------------------------------------------------------------------

def run(
    task: str,
    *,
    stock_code: Optional[str] = None,
    year: Optional[int] = None,
    year_month: Optional[str] = None,
    industry_code: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    可复用的 maintenance_l4 执行入口（供总控调用）。

    本函数只执行单个 task（不支持 task=all 的自动派发，总控需逐个传入）。

    Returns:
        {"success": bool, "executed_tasks": [...], "failed_tasks": [...], "receipt_path": str, "results": {...}}
    """
    # 参数校验
    err = _validate_task_params_for_run(task, stock_code, year, year_month, industry_code)
    if err:
        print(f"[ERROR] {err}")
        return {
            "success": False,
            "executed_tasks": [],
            "failed_tasks": [{"task": task, "error": err}],
            "receipt_path": None,
            "results": {},
        }

    print(f"[START] maintenance_l4 task={task} dry_run={dry_run}")

    outcome = _run_single_task(
        task,
        stock_code=stock_code,
        year=year,
        year_month=year_month,
        industry_code=industry_code,
        dry_run=dry_run,
    )

    executed_tasks: List[str] = []
    failed_tasks: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}

    if outcome["success"]:
        executed_tasks.append(task)
    else:
        failed_tasks.append({
            "task": task,
            "error": outcome.get("error"),
        })

    results[task] = outcome.get("data")

    receipt_path = _build_receipt_path(task)
    _write_receipt(
        receipt_path=receipt_path,
        task=task,
        stock_code=stock_code,
        year=year,
        year_month=year_month,
        industry_code=industry_code,
        dry_run=dry_run,
        executed_tasks=executed_tasks,
        failed_tasks=failed_tasks,
        results=results,
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"task           : {task}")
    print(f"dry_run        : {dry_run}")
    print(f"executed       : {len(executed_tasks)}")
    print(f"failed         : {len(failed_tasks)}")
    if failed_tasks:
        for ft in failed_tasks:
            print(f"  - {ft['task']}: {ft['error']}")
    print(f"receipt_path   : {receipt_path}")
    print("=" * 60)

    return {
        "success": len(failed_tasks) == 0,
        "executed_tasks": executed_tasks,
        "failed_tasks": failed_tasks,
        "receipt_path": receipt_path,
        "results": results,
    }


def _validate_task_params_for_run(
    task: str,
    stock_code: Optional[str],
    year: Optional[int],
    year_month: Optional[str],
    industry_code: Optional[str],
) -> Optional[str]:
    """为 run() 提供的参数校验（不使用 argparse.Namespace）。"""
    required = TASK_REQUIREMENTS.get(task)
    if required is None:
        return f"unknown task: {task}"

    params = {
        "stock_code": stock_code,
        "year": year,
        "year_month": year_month,
        "industry_code": industry_code,
    }
    missing = []
    for param in required:
        value = params.get(param)
        if value is None or str(value).strip() == "":
            missing.append(f"--{param}")

    if missing:
        return f"task '{task}' missing required params: {', '.join(missing)}"

    return None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Layer-4 maintenance/rebuild job. Calls MaintenanceService directly."
    )
    parser.add_argument(
        "--task",
        required=True,
        choices=[
            "announcement_summary_monthly",
            "drug_pipeline_summary_yearly",
            "financial_metric_summary_yearly",
            "industry_news_summary_monthly",
            "all",
        ],
        help="Maintenance task to execute.",
    )
    parser.add_argument("--stock-code", default=None, help="Target stock_code.")
    parser.add_argument("--year", type=int, default=None, help="Target year (e.g., 2026).")
    parser.add_argument(
        "--year-month", default=None, help="Target year-month (YYYY-MM, e.g., 2026-03)."
    )
    parser.add_argument("--industry-code", default=None, help="Target industry_code.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned tasks without calling service.")
    args = parser.parse_args()

    # 1. 确定任务列表
    if args.task == "all":
        task_list = _resolve_tasks_for_all(args)
        if not task_list:
            print("[INFO] task=all but no sufficient params provided to run any sub-task.")
            print("  Provide at least one of:")
            print("    --stock-code + --year-month  → announcement_summary_monthly")
            print("    --stock-code + --year        → drug_pipeline + financial_metric")
            print("    --industry-code + --year-month → industry_news_summary")
            sys.exit(0)
    else:
        err = _validate_task_params(args.task, args)
        if err:
            print(f"[ERROR] {err}")
            sys.exit(1)
        task_list = [args.task]

    # 2. 执行
    print(f"[START] maintenance_l4 task={args.task} dry_run={args.dry_run}")
    print(f"  tasks to execute: {task_list}")

    executed_tasks: List[str] = []
    failed_tasks: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}

    for task_name in task_list:
        print(f"\n[EXECUTE] {task_name}")
        outcome = _run_single_task(
            task_name,
            stock_code=args.stock_code,
            year=args.year,
            year_month=args.year_month,
            industry_code=args.industry_code,
            dry_run=args.dry_run,
        )

        if outcome["success"]:
            executed_tasks.append(task_name)
        else:
            failed_tasks.append({
                "task": task_name,
                "error": outcome.get("error"),
            })

        results[task_name] = outcome.get("data")

    # 3. 写 receipt
    receipt_path = _build_receipt_path(args.task)
    _write_receipt(
        receipt_path=receipt_path,
        task=args.task,
        stock_code=args.stock_code,
        year=args.year,
        year_month=args.year_month,
        industry_code=args.industry_code,
        dry_run=args.dry_run,
        executed_tasks=executed_tasks,
        failed_tasks=failed_tasks,
        results=results,
    )

    # 4. 控制台 summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"task           : {args.task}")
    print(f"dry_run        : {args.dry_run}")
    print(f"executed       : {len(executed_tasks)}")
    print(f"failed         : {len(failed_tasks)}")
    if failed_tasks:
        for ft in failed_tasks:
            print(f"  - {ft['task']}: {ft['error']}")
    print(f"receipt_path   : {receipt_path}")
    print("=" * 60)

    if failed_tasks:
        sys.exit(1)


if __name__ == "__main__":
    main()
