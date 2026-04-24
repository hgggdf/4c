"""
ingest_center / run_announcement_l3.py
=====================================

第3层公告事件类 job。

职责：
    从第2层 E2E staging 文件中读取公告事件数据，
    直调 AnnouncementWriteService 写入五类事件表。
    不走 router，不走 HTTP，完全通过 ServiceContainer 内部调用。

涵盖类别：
    - structured_announcements  → AnnouncementStructuredHot（需 announcement_id 反查）
    - drug_approvals            → DrugApprovalHot
    - clinical_trials           → ClinicalTrialEventHot
    - procurement_events        → CentralizedProcurementEventHot
    - regulatory_risks          → RegulatoryRiskEventHot

用法示例：
    python -m ingest_center.run_announcement_l3 --category all --dry-run
    python -m ingest_center.run_announcement_l3 --category structured_announcements
    python -m ingest_center.run_announcement_l3 --category drug_approvals
    python -m ingest_center.run_announcement_l3 --staging-dir backend/crawler/staging/e2e --category all
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

from app.service.write_requests import BatchItemsRequest

from . import common
from . import config
from .id_resolver import resolve_announcement_id
from .service_runtime import get_container


# ---------------------------------------------------------------------------
# 字段白名单（与 ORM 模型对齐，排除 id / created_at）
# ---------------------------------------------------------------------------

CATEGORY_FIELD_WHITELIST: Dict[str, List[str]] = {
    "structured_announcements": [
        "stock_code",
        "category",
        "summary_text",
        "key_fields_json",
        "signal_type",
        "risk_level",
    ],
    "drug_approvals": [
        "stock_code",
        "drug_name",
        "approval_type",
        "approval_date",
        "indication",
        "drug_stage",
        "is_innovative_drug",
        "review_status",
        "market_scope",
        "source_announcement_id",
        "source_type",
        "source_url",
    ],
    "clinical_trials": [
        "stock_code",
        "drug_name",
        "trial_phase",
        "event_type",
        "event_date",
        "indication",
        "summary_text",
        "source_announcement_id",
        "source_type",
        "source_url",
    ],
    "procurement_events": [
        "stock_code",
        "drug_name",
        "procurement_round",
        "bid_result",
        "price_change_ratio",
        "event_date",
        "impact_summary",
        "source_announcement_id",
        "source_type",
        "source_url",
    ],
    "regulatory_risks": [
        "stock_code",
        "risk_type",
        "event_date",
        "risk_level",
        "summary_text",
        "source_announcement_id",
        "source_type",
        "source_url",
    ],
}

# 事件类关键必填字段（structured_announcements 单独校验）
EVENT_REQUIRED_FIELDS = ["stock_code"]


# ---------------------------------------------------------------------------
# 数据读取与过滤
# ---------------------------------------------------------------------------

def _discover_staging_files(staging_dir: str) -> List[str]:
    """发现符合命名规则的 staging 文件。"""
    pattern = os.path.join(staging_dir, "e2e_announcement_raw_*.json")
    files = sorted(glob.glob(pattern))
    return files


def _load_json_file(path: str) -> Optional[Dict[str, Any]]:
    """安全读取 JSON 文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [WARN] failed to load {path}: {exc}")
        return None


def _extract_event_items(
    data: Dict[str, Any],
    category: str,
) -> tuple[List[Dict[str, Any]], int]:
    """
    从 staging JSON 的 payload 中提取事件类原始 items，并做字段白名单过滤。

    Returns:
        (filtered_items, skipped_invalid_count)
    """
    payload = data.get("payload") or {}
    raw_items: List[Dict[str, Any]] = payload.get(category) or []
    if not raw_items:
        return [], 0

    whitelist = CATEGORY_FIELD_WHITELIST.get(category, [])
    filtered: List[Dict[str, Any]] = []
    skipped = 0

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            skipped += 1
            continue

        clean = {k: v for k, v in item.items() if k in whitelist}

        missing_required = [f for f in EVENT_REQUIRED_FIELDS if clean.get(f) is None]
        if missing_required:
            print(f"  [SKIP] {category}[{idx}] missing required fields: {missing_required}")
            skipped += 1
            continue

        filtered.append(clean)

    return filtered, skipped


def _extract_structured_items(
    data: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], int, int, int, int]:
    """
    从 staging JSON 的 payload 中提取 structured_announcements，
    做字段白名单过滤 + announcement_id 反查注入。

    Returns:
        (filtered_items, skipped_invalid, resolve_attempted, resolve_success, resolve_failed)
    """
    payload = data.get("payload") or {}
    raw_items: List[Dict[str, Any]] = payload.get("structured_announcements") or []
    if not raw_items:
        return [], 0, 0, 0, 0

    whitelist = CATEGORY_FIELD_WHITELIST.get("structured_announcements", [])
    filtered: List[Dict[str, Any]] = []
    skipped = 0
    attempted = 0
    success = 0
    failed = 0

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            skipped += 1
            continue

        # 1. 提取反查键
        stock_code = item.get("stock_code")
        title = item.get("title")
        publish_date = item.get("publish_date")

        if not stock_code or not title or not publish_date:
            print(
                f"  [SKIP] structured_announcements[{idx}] "
                f"missing resolve keys (stock_code={stock_code}, title={title}, publish_date={publish_date})"
            )
            skipped += 1
            continue

        # 2. 字段白名单过滤
        clean = {k: v for k, v in item.items() if k in whitelist}
        clean["stock_code"] = stock_code

        # 3. 反查 announcement_id
        attempted += 1
        ann_id = resolve_announcement_id(
            stock_code=str(stock_code),
            title=str(title),
            publish_date=str(publish_date),
        )

        if ann_id is None:
            print(
                f"  [SKIP] structured_announcements[{idx}] announcement_id not found "
                f"for (stock_code={stock_code}, title={title!r}, publish_date={publish_date})"
            )
            failed += 1
            skipped += 1
            continue

        clean["announcement_id"] = ann_id
        success += 1
        filtered.append(clean)

    return filtered, skipped, attempted, success, failed


def _collect_items_by_category(
    files: List[str],
    categories: List[str],
) -> Dict[str, Dict[str, Any]]:
    """
    从所有 staging 文件中收集各类别事件数据。

    Returns:
        {
            "structured_announcements": {
                "items": [...],
                "read_count": 10,
                "skipped_invalid": 2,
                "resolve_attempted": 8,
                "resolve_success": 6,
                "resolve_failed": 2,
            },
            "drug_approvals": {
                "items": [...],
                "read_count": 10,
                "skipped_invalid": 0,
            },
            ...
        }
    """
    result: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        result[cat] = {
            "items": [],
            "read_count": 0,
            "skipped_invalid": 0,
            "resolve_attempted": 0,
            "resolve_success": 0,
            "resolve_failed": 0,
        }

    for path in files:
        print(f"  [READ] {os.path.basename(path)}")
        data = _load_json_file(path)
        if data is None:
            continue

        for cat in categories:
            if cat == "structured_announcements":
                items, skipped, attempted, success, failed = _extract_structured_items(data)
                result[cat]["resolve_attempted"] += attempted
                result[cat]["resolve_success"] += success
                result[cat]["resolve_failed"] += failed
            else:
                items, skipped = _extract_event_items(data, cat)

            result[cat]["items"].extend(items)
            result[cat]["read_count"] += len(items) + skipped
            result[cat]["skipped_invalid"] += skipped

    return result


# ---------------------------------------------------------------------------
# Service 调用
# ---------------------------------------------------------------------------

def _call_service_for_category(
    category: str,
    items: List[Dict[str, Any]],
    dry_run: bool,
) -> Dict[str, Any]:
    """
    对指定类别直调 AnnouncementWriteService。

    Returns:
        {"success": bool, "data": ..., "error": ...}
    """
    container = get_container()

    if dry_run:
        print(f"  [DRY-RUN] would upsert {len(items)} {category}")
        return {"success": True, "data": {"dry_run": True, "count": len(items)}, "error": None}

    if not items:
        print(f"  [SKIP] {category}: no items to upsert")
        return {"success": True, "data": {"count": 0}, "error": None}

    req = BatchItemsRequest(items=items)

    try:
        if category == "structured_announcements":
            result = container.announcement_write.batch_upsert_structured_announcements(req)
        elif category == "drug_approvals":
            result = container.announcement_write.batch_upsert_drug_approvals(req)
        elif category == "clinical_trials":
            result = container.announcement_write.batch_upsert_clinical_trials(req)
        elif category == "procurement_events":
            result = container.announcement_write.batch_upsert_procurement_events(req)
        elif category == "regulatory_risks":
            result = container.announcement_write.batch_upsert_regulatory_risks(req)
        else:
            return {"success": False, "data": None, "error": f"unknown category: {category}"}

        if result.success:
            print(f"  [DONE] {category}: {result.data}")
            return {"success": True, "data": result.data, "error": None}
        else:
            print(f"  [FAIL] {category}: {result.message} ({result.error_code})")
            return {
                "success": False,
                "data": result.data,
                "error": f"{result.message} ({result.error_code})",
            }

    except Exception as exc:
        print(f"  [FAIL] {category}: {exc}")
        return {"success": False, "data": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def _build_receipt_path(category: str) -> str:
    """生成 receipt 文件路径。"""
    ts = common.now_iso().replace(":", "").replace("+", "_")
    filename = f"announcement_l3_{category}_{ts}.json"
    return os.path.join(config.RECEIPT_DIR, filename)


def _write_receipt(
    *,
    receipt_path: str,
    category: str,
    staging_dir: str,
    dry_run: bool,
    processed_files: int,
    per_category_counts: Dict[str, Any],
    executed_categories: List[str],
    failed_categories: List[Dict[str, Any]],
    results: Dict[str, Any],
) -> str:
    """构造并写入 receipt 文件。"""
    status = "validated" if dry_run else ("done" if not failed_categories else "failed")
    success = dry_run or (len(failed_categories) == 0 and len(executed_categories) > 0)

    receipt = {
        "job_type": "announcement_l3",
        "category": category,
        "staging_dir": staging_dir,
        "dry_run": dry_run,
        "processed_files": processed_files,
        "per_category_counts": per_category_counts,
        "executed_categories": executed_categories,
        "failed_categories": failed_categories,
        "results": results,
        "status": status,
        "success": success,
        "created_at": common.now_iso(),
    }

    common.write_receipt(receipt_path, receipt)
    return receipt_path


# ---------------------------------------------------------------------------
# 可复用执行入口
# ---------------------------------------------------------------------------

def run(
    staging_dir: Optional[str] = None,
    category: str = "all",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    可复用的 announcement_l3 执行入口（供总控调用）。

    Returns:
        {"success": bool, "executed_categories": [...], "failed_categories": [...], "receipt_path": str}
    """
    if staging_dir is None:
        staging_dir = os.path.join(config.PROJECT_ROOT, "crawler", "staging", "e2e")

    if category == "all":
        categories = list(CATEGORY_FIELD_WHITELIST.keys())
    else:
        categories = [category]

    print(f"[START] announcement_l3 category={category} dry_run={dry_run}")
    print(f"  staging_dir: {staging_dir}")

    files = _discover_staging_files(staging_dir)
    print(f"  discovered {len(files)} staging file(s)")

    if not files:
        print("[INFO] no staging files found, exiting.")
        return {"success": True, "executed_categories": [], "failed_categories": [], "receipt_path": None}

    print("\n[COLLECT] reading and filtering items from staging files...")
    collected = _collect_items_by_category(files, categories)

    for cat in categories:
        info = collected[cat]
        extra = ""
        if cat == "structured_announcements":
            extra = (
                f" resolved={info['resolve_success']}/{info['resolve_attempted']}"
                f" failed_resolve={info['resolve_failed']}"
            )
        print(
            f"  {cat}: read={info['read_count']} filtered={len(info['items'])}"
            f" skipped={info['skipped_invalid']}{extra}"
        )

    print("\n[EXECUTE] calling services...")
    executed_categories: List[str] = []
    failed_categories: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}

    for cat in categories:
        items = collected[cat]["items"]
        if not items and not dry_run:
            print(f"\n[SKIP] {cat}: no items to process")
            continue

        print(f"\n[EXECUTE] {cat} ({len(items)} items)")
        outcome = _call_service_for_category(cat, items, dry_run=dry_run)

        if outcome["success"]:
            executed_categories.append(cat)
        else:
            failed_categories.append({
                "category": cat,
                "error": outcome.get("error"),
            })

        results[cat] = outcome.get("data")

    per_category_counts = {}
    for cat in categories:
        info = collected[cat]
        per_category_counts[cat] = {
            "read": info["read_count"],
            "filtered": len(info["items"]),
            "skipped_invalid": info["skipped_invalid"],
        }
        if cat == "structured_announcements":
            per_category_counts[cat]["resolve_attempted"] = info["resolve_attempted"]
            per_category_counts[cat]["resolve_success"] = info["resolve_success"]
            per_category_counts[cat]["resolve_failed"] = info["resolve_failed"]

    receipt_path = _build_receipt_path(category)
    _write_receipt(
        receipt_path=receipt_path,
        category=category,
        staging_dir=staging_dir,
        dry_run=dry_run,
        processed_files=len(files),
        per_category_counts=per_category_counts,
        executed_categories=executed_categories,
        failed_categories=failed_categories,
        results=results,
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"category          : {category}")
    print(f"staging_dir       : {staging_dir}")
    print(f"dry_run           : {dry_run}")
    print(f"processed_files   : {len(files)}")
    for cat in categories:
        info = collected[cat]
        status_str = (
            "done"
            if cat in executed_categories
            else ("failed" if any(fc["category"] == cat for fc in failed_categories) else "skipped")
        )
        line = (
            f"  {cat:26s}: read={info['read_count']:3d} filtered={len(info['items']):3d}"
            f" skipped={info['skipped_invalid']:3d} [{status_str}]"
        )
        if cat == "structured_announcements":
            line += (
                f"  resolved={info['resolve_success']}/{info['resolve_attempted']}"
            )
        print(line)
    print(f"executed          : {len(executed_categories)}")
    print(f"failed            : {len(failed_categories)}")
    if failed_categories:
        for fc in failed_categories:
            print(f"  - {fc['category']}: {fc['error']}")
    print(f"receipt_path      : {receipt_path}")
    print("=" * 70)

    return {
        "success": len(failed_categories) == 0,
        "executed_categories": executed_categories,
        "failed_categories": failed_categories,
        "receipt_path": receipt_path,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Layer-3 announcement events ingest job. Calls AnnouncementWriteService directly."
    )
    parser.add_argument(
        "--staging-dir",
        default=os.path.join(config.PROJECT_ROOT, "crawler", "staging", "e2e"),
        help="Directory containing e2e_announcement_raw_*.json staging files.",
    )
    parser.add_argument(
        "--category",
        default="all",
        choices=[
            "structured_announcements",
            "drug_approvals",
            "clinical_trials",
            "procurement_events",
            "regulatory_risks",
            "all",
        ],
        help="Event category to process.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned tasks without calling service.")
    args = parser.parse_args()

    result = run(
        staging_dir=args.staging_dir,
        category=args.category,
        dry_run=args.dry_run,
    )
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
