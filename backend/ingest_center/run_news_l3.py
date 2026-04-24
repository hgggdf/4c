"""
ingest_center / run_news_l3.py
=============================

第3层新闻 job。

职责：
    从第2层 E2E staging 文件中读取新闻结构化/映射/影响数据，
    直调 NewsWriteService 写入四类表。
    不走 router，不走 HTTP，完全通过 ServiceContainer 内部调用。

涵盖类别：
    - news_structured        → NewsStructuredHot（需 news_id 反查）
    - news_industry_maps     → NewsIndustryMapHot（需 news_id 反查，按 news_id 分组 replace）
    - news_company_maps      → NewsCompanyMapHot（需 news_id 反查，按 news_id 分组 replace）
    - industry_impact_events → IndustryImpactEventHot（需 source_news_id 反查）

用法示例：
    python -m ingest_center.run_news_l3 --category all --dry-run
    python -m ingest_center.run_news_l3 --category news_structured
    python -m ingest_center.run_news_l3 --category news_company_maps
    python -m ingest_center.run_news_l3 --staging-dir backend/crawler/staging/e2e --category all
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

from app.service.write_requests import (
    BatchItemsRequest,
    ReplaceNewsCompanyMapRequest,
    ReplaceNewsIndustryMapRequest,
)

from . import common
from . import config
from .id_resolver import resolve_news_id
from .service_runtime import get_container


# ---------------------------------------------------------------------------
# 字段白名单（与 ORM 模型对齐，排除 id / created_at）
# ---------------------------------------------------------------------------

CATEGORY_FIELD_WHITELIST: Dict[str, List[str]] = {
    "news_structured": [
        "news_id",
        "topic_category",
        "summary_text",
        "keywords_json",
        "signal_type",
        "impact_level",
        "impact_horizon",
        "sentiment_label",
        "confidence_score",
    ],
    "news_industry_maps": [
        "news_id",
        "industry_code",
        "impact_direction",
        "impact_strength",
        "reason_text",
    ],
    "news_company_maps": [
        "news_id",
        "stock_code",
        "impact_direction",
        "impact_strength",
        "reason_text",
    ],
    "industry_impact_events": [
        "source_news_id",
        "industry_code",
        "event_name",
        "impact_direction",
        "impact_level",
        "impact_horizon",
        "summary_text",
        "event_date",
    ],
}

# staging 中 industry_impact_events 可能使用别名，映射到 ORM 字段
IMPACT_EVENT_FIELD_ALIASES = {
    "news_id": "source_news_id",
    "event_type": "event_name",
}


# ---------------------------------------------------------------------------
# 数据读取与过滤
# ---------------------------------------------------------------------------

def _discover_staging_files(staging_dir: str) -> List[str]:
    """发现符合命名规则的 staging 文件。"""
    pattern = os.path.join(staging_dir, "e2e_news_raw_*.json")
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


def _resolve_news_id_from_key(key: Any) -> Optional[int]:
    """
    将 staging 字典的 key 解析为 news_id。

    JSON object key 始终为字符串，因此：
    - 先尝试解析为 int（即 key 本身就是 news_id 的字符串形式）
    - 若失败则当作 news_uid，通过 resolve_news_id 反查
    """
    if isinstance(key, int):
        return key
    if isinstance(key, str):
        try:
            return int(key)
        except ValueError:
            return resolve_news_id(news_uid=key)
    return None


def _extract_array_items_with_resolve(
    data: Dict[str, Any],
    category: str,
    resolve_key_field: str,
    inject_field: str,
) -> tuple[List[Dict[str, Any]], int, int, int, int]:
    """
    从 staging payload 中提取数组类 items，做字段白名单过滤 + news_id 反查注入。

    Args:
        data: staging JSON dict
        category: payload 中的字段名
        resolve_key_field: 用于反查的字段名（如 "news_uid"）
        inject_field: 注入到 clean item 中的字段名（如 "news_id"）

    Returns:
        (filtered_items, skipped_invalid, resolve_attempted, resolve_success, resolve_failed)
    """
    payload = data.get("payload") or {}
    raw_items: List[Dict[str, Any]] = payload.get(category) or []
    if not raw_items:
        return [], 0, 0, 0, 0

    whitelist = CATEGORY_FIELD_WHITELIST.get(category, [])
    filtered: List[Dict[str, Any]] = []
    skipped = 0
    attempted = 0
    success = 0
    failed = 0

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            skipped += 1
            continue

        resolve_key = item.get(resolve_key_field)
        if not resolve_key:
            print(
                f"  [SKIP] {category}[{idx}] missing resolve key '{resolve_key_field}'"
            )
            skipped += 1
            continue

        # 字段白名单过滤
        clean = {k: v for k, v in item.items() if k in whitelist}

        # 处理别名映射（如 event_type -> event_name）
        for alias, target in IMPACT_EVENT_FIELD_ALIASES.items():
            if alias in item and target not in clean:
                clean[target] = item[alias]

        # 反查 ID
        attempted += 1
        nid = resolve_news_id(news_uid=str(resolve_key))
        if nid is None:
            print(
                f"  [SKIP] {category}[{idx}] {inject_field} not found for news_uid={resolve_key!r}"
            )
            failed += 1
            skipped += 1
            continue

        clean[inject_field] = nid
        success += 1
        filtered.append(clean)

    return filtered, skipped, attempted, success, failed


def _extract_dict_grouped_items_with_resolve(
    data: Dict[str, Any],
    category: str,
) -> tuple[Dict[int, List[Dict[str, Any]]], int, int, int, int]:
    """
    从 staging payload 中提取字典类 items（news_industry_maps / news_company_maps），
    做字段白名单过滤 + 按 news_id 分组。

    staging 格式预期：{"news_uid_or_news_id": [item1, item2, ...], ...}

    Returns:
        (grouped_items, skipped_invalid, resolve_attempted, resolve_success, resolve_failed)
        grouped_items: {news_id: [clean_item, ...]}
    """
    payload = data.get("payload") or {}
    raw_maps: Dict[str, Any] = payload.get(category) or {}
    if not raw_maps:
        return {}, 0, 0, 0, 0

    whitelist = CATEGORY_FIELD_WHITELIST.get(category, [])
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    skipped = 0
    attempted = 0
    success = 0
    failed = 0

    for key, items in raw_maps.items():
        # 解析 key 为 news_id
        attempted += 1
        news_id = _resolve_news_id_from_key(key)
        if news_id is None:
            print(
                f"  [SKIP] {category} group key={key!r} cannot resolve to news_id"
            )
            failed += 1
            skipped += len(items) if isinstance(items, list) else 0
            continue

        success += 1

        if not isinstance(items, list):
            skipped += 1
            continue

        filtered_items: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                skipped += 1
                continue

            clean = {k: v for k, v in item.items() if k in whitelist}
            # news_id 通过外层 grouped dict key 传递，不再重复注入 item
            # 避免 ReplaceNews*MapRequest(news_id=..., items=[..., news_id, ...]) 重复传参
            filtered_items.append(clean)

        if news_id not in grouped:
            grouped[news_id] = []
        grouped[news_id].extend(filtered_items)

    return grouped, skipped, attempted, success, failed


def _collect_items_by_category(
    files: List[str],
    categories: List[str],
) -> Dict[str, Dict[str, Any]]:
    """
    从所有 staging 文件中收集各类别数据。

    返回结构：
        {
            "news_structured": {
                "items": [...],           # List[dict]
                "read_count": 10,
                "skipped_invalid": 2,
                "resolve_attempted": 8,
                "resolve_success": 6,
                "resolve_failed": 2,
            },
            "news_industry_maps": {
                "items": {1: [...], 2: [...]},  # Dict[int, List[dict]]
                "read_count": 10,
                "skipped_invalid": 0,
                "resolve_attempted": 4,
                "resolve_success": 4,
                "resolve_failed": 0,
            },
            ...
        }
    """
    result: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        result[cat] = {
            "items": [] if cat in ("news_structured", "industry_impact_events") else {},
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
            if cat == "news_structured":
                items, skipped, attempted, success, failed = _extract_array_items_with_resolve(
                    data, cat, resolve_key_field="news_uid", inject_field="news_id"
                )
                result[cat]["items"].extend(items)  # type: ignore[union-attr]
            elif cat == "industry_impact_events":
                items, skipped, attempted, success, failed = _extract_array_items_with_resolve(
                    data, cat, resolve_key_field="news_uid", inject_field="source_news_id"
                )
                result[cat]["items"].extend(items)  # type: ignore[union-attr]
            elif cat in ("news_industry_maps", "news_company_maps"):
                grouped, skipped, attempted, success, failed = _extract_dict_grouped_items_with_resolve(
                    data, cat
                )
                # 合并 grouped dict
                existing: Dict[int, List[Dict[str, Any]]] = result[cat]["items"]  # type: ignore[assignment]
                for nid, items_list in grouped.items():
                    if nid not in existing:
                        existing[nid] = []
                    existing[nid].extend(items_list)
            else:
                items, skipped = [], 0
                attempted = success = failed = 0

            result[cat]["read_count"] += len(items if cat in ("news_structured", "industry_impact_events") else []) + skipped
            # 对字典类型，read_count 需要单独计算
            if cat in ("news_industry_maps", "news_company_maps"):
                payload = data.get("payload") or {}
                raw_maps = payload.get(cat) or {}
                total_items = 0
                for items_list in raw_maps.values():
                    if isinstance(items_list, list):
                        total_items += len(items_list)
                result[cat]["read_count"] += total_items

            result[cat]["skipped_invalid"] += skipped
            result[cat]["resolve_attempted"] += attempted
            result[cat]["resolve_success"] += success
            result[cat]["resolve_failed"] += failed

    return result


# ---------------------------------------------------------------------------
# Service 调用
# ---------------------------------------------------------------------------

def _call_service_for_category(
    category: str,
    items: Any,
    dry_run: bool,
) -> Dict[str, Any]:
    """
    对指定类别直调 NewsWriteService。

    Args:
        category: 类别名。
        items: 对数组类为 List[dict]，对字典类为 Dict[int, List[dict]]。
        dry_run: 是否 dry-run。

    Returns:
        {"success": bool, "data": ..., "error": ...}
    """
    container = get_container()

    if dry_run:
        if isinstance(items, dict):
            total = sum(len(v) for v in items.values())
            print(f"  [DRY-RUN] would upsert {total} {category} across {len(items)} group(s)")
        else:
            print(f"  [DRY-RUN] would upsert {len(items)} {category}")
        return {"success": True, "data": {"dry_run": True, "count": len(items) if isinstance(items, list) else sum(len(v) for v in items.values())}, "error": None}

    # 数组类 batch upsert
    if category == "news_structured":
        if not items:
            print(f"  [SKIP] {category}: no items")
            return {"success": True, "data": {"count": 0}, "error": None}
        req = BatchItemsRequest(items=items)
        try:
            result = container.news_write.batch_upsert_news_structured(req)
            return _wrap_result(category, result)
        except Exception as exc:
            return _wrap_exc(category, exc)

    if category == "industry_impact_events":
        if not items:
            print(f"  [SKIP] {category}: no items")
            return {"success": True, "data": {"count": 0}, "error": None}
        req = BatchItemsRequest(items=items)
        try:
            result = container.news_write.batch_upsert_industry_impact_events(req)
            return _wrap_result(category, result)
        except Exception as exc:
            return _wrap_exc(category, exc)

    # 字典类 replace（按 news_id 分组）
    if category == "news_industry_maps":
        return _call_replace_groups(
            category, items, dry_run,
            lambda nid, itms: container.news_write.replace_news_industry_map(
                ReplaceNewsIndustryMapRequest(news_id=nid, items=itms)
            ),
        )

    if category == "news_company_maps":
        return _call_replace_groups(
            category, items, dry_run,
            lambda nid, itms: container.news_write.replace_news_company_map(
                ReplaceNewsCompanyMapRequest(news_id=nid, items=itms)
            ),
        )

    return {"success": False, "data": None, "error": f"unknown category: {category}"}


def _call_replace_groups(
    category: str,
    grouped: Dict[int, List[Dict[str, Any]]],
    dry_run: bool,
    call_fn,
) -> Dict[str, Any]:
    """对 news_industry_maps / news_company_maps 按 news_id 分组调用 replace。"""
    if not grouped:
        print(f"  [SKIP] {category}: no groups")
        return {"success": True, "data": {"group_count": 0, "total": 0}, "error": None}

    if dry_run:
        total = sum(len(v) for v in grouped.values())
        print(f"  [DRY-RUN] would replace {total} {category} across {len(grouped)} group(s)")
        return {"success": True, "data": {"dry_run": True, "group_count": len(grouped), "total": total}, "error": None}

    details: List[Dict[str, Any]] = []
    all_ok = True

    for news_id, items in sorted(grouped.items()):
        if not items:
            continue
        # 从 item 中移除 news_id，防止与外层 request.news_id 重复传入 ORM
        clean_items = [{k: v for k, v in item.items() if k != "news_id"} for item in items]
        try:
            result = call_fn(news_id, clean_items)
            if result.success:
                print(f"  [DONE] {category} news_id={news_id}: {result.data}")
                details.append({"news_id": news_id, "ok": True, "data": result.data})
            else:
                print(f"  [FAIL] {category} news_id={news_id}: {result.message} ({result.error_code})")
                details.append({"news_id": news_id, "ok": False, "error": f"{result.message} ({result.error_code})"})
                all_ok = False
        except Exception as exc:
            print(f"  [FAIL] {category} news_id={news_id}: {exc}")
            details.append({"news_id": news_id, "ok": False, "error": str(exc)})
            all_ok = False

    total = sum(len(v) for v in grouped.values())
    return {
        "success": all_ok,
        "data": {"group_count": len(grouped), "total": total, "details": details},
        "error": None if all_ok else "some groups failed",
    }


def _wrap_result(category: str, result) -> Dict[str, Any]:
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


def _wrap_exc(category: str, exc: Exception) -> Dict[str, Any]:
    print(f"  [FAIL] {category}: {exc}")
    return {"success": False, "data": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def _build_receipt_path(category: str) -> str:
    """生成 receipt 文件路径。"""
    ts = common.now_iso().replace(":", "").replace("+", "_")
    filename = f"news_l3_{category}_{ts}.json"
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
        "job_type": "news_l3",
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
    可复用的 news_l3 执行入口（供总控调用）。

    Returns:
        {"success": bool, "executed_categories": [...], "failed_categories": [...], "receipt_path": str}
    """
    if staging_dir is None:
        staging_dir = os.path.join(config.PROJECT_ROOT, "crawler", "staging", "e2e")

    if category == "all":
        categories = list(CATEGORY_FIELD_WHITELIST.keys())
    else:
        categories = [category]

    print(f"[START] news_l3 category={category} dry_run={dry_run}")
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
        extra = (
            f" resolved={info['resolve_success']}/{info['resolve_attempted']}"
            f" failed_resolve={info['resolve_failed']}"
        )
        if cat in ("news_industry_maps", "news_company_maps"):
            group_count = len(info["items"]) if info["items"] else 0
            total = sum(len(v) for v in info["items"].values()) if info["items"] else 0
            print(
                f"  {cat}: read={info['read_count']} groups={group_count} total={total}"
                f" skipped={info['skipped_invalid']}{extra}"
            )
        else:
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
        has_content = False
        if isinstance(items, list) and items:
            has_content = True
        elif isinstance(items, dict) and items:
            has_content = True

        if not has_content and not dry_run:
            print(f"\n[SKIP] {cat}: no items to process")
            continue

        if isinstance(items, dict):
            total = sum(len(v) for v in items.values()) if items else 0
            print(f"\n[EXECUTE] {cat} ({total} items in {len(items)} group(s))")
        else:
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
        count = {
            "read": info["read_count"],
            "skipped_invalid": info["skipped_invalid"],
            "resolve_attempted": info["resolve_attempted"],
            "resolve_success": info["resolve_success"],
            "resolve_failed": info["resolve_failed"],
        }
        if cat in ("news_industry_maps", "news_company_maps"):
            count["group_count"] = len(info["items"]) if info["items"] else 0
            count["total"] = sum(len(v) for v in info["items"].values()) if info["items"] else 0
        else:
            count["filtered"] = len(info["items"])
        per_category_counts[cat] = count

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
        if cat in ("news_industry_maps", "news_company_maps"):
            group_count = len(info["items"]) if info["items"] else 0
            total = sum(len(v) for v in info["items"].values()) if info["items"] else 0
            line = (
                f"  {cat:26s}: read={info['read_count']:3d} groups={group_count:3d} total={total:3d}"
                f" skipped={info['skipped_invalid']:3d} [{status_str}]"
            )
        else:
            line = (
                f"  {cat:26s}: read={info['read_count']:3d} filtered={len(info['items']):3d}"
                f" skipped={info['skipped_invalid']:3d} [{status_str}]"
            )
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
        description="Layer-3 news structured/mappings/impact ingest job. Calls NewsWriteService directly."
    )
    parser.add_argument(
        "--staging-dir",
        default=os.path.join(config.PROJECT_ROOT, "crawler", "staging", "e2e"),
        help="Directory containing e2e_news_raw_*.json staging files.",
    )
    parser.add_argument(
        "--category",
        default="all",
        choices=[
            "news_structured",
            "news_industry_maps",
            "news_company_maps",
            "industry_impact_events",
            "all",
        ],
        help="Category to process.",
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
