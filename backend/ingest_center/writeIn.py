"""
ingest_center / writeIn.py
==========================

外部爬虫数据入库桥接模块。

职责：
    1. 读取 Data/ 目录下外部爬虫投放的 JSON 文件
    2. 按文件名映射到对应的 service action，直调 ServiceContainer 入库
    3. 入库前清空对应 manifests 目录中的旧 manifest，防止重复入库
    4. 入库后生成 manifest 指引文件到 manifests_openclaw/ 供审计追溯
    5. 入库完成后删除已处理的 Data/ 中的 JSON 文件

用法：
    python -m ingest_center.writeIn
    python -m ingest_center.writeIn --dry-run
    python -m ingest_center.writeIn --category company
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import common
from .service_runtime import get_container

from app.service.write_requests import (
    BatchItemsRequest,
    IngestAnnouncementPackageRequest,
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    IngestNewsPackageRequest,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")
MANIFEST_OUT_DIR = os.path.join(os.path.dirname(__file__), "manifests_openclaw")
RECEIPT_DIR = os.path.join(os.path.dirname(__file__), "receipts")

# 文件名 -> (data_category, service调用方式)
FILE_CATEGORY_MAP: Dict[str, str] = {
    "company.json": "company",
    "stock_daily.json": "stock_daily",
    "announcement.json": "announcement",
    "news.json": "news",
    "macro.json": "macro",
    "financial.json": "financial",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [ERROR] failed to load {path}: {exc}")
        return None


def _clean_old_manifests(category: str) -> int:
    """删除 manifests_openclaw/ 中该 category 的旧 manifest 文件。"""
    pattern = os.path.join(MANIFEST_OUT_DIR, f"{category}_*.json")
    old_files = glob.glob(pattern)
    for f in old_files:
        os.remove(f)
    return len(old_files)


def _write_manifest(category: str, data_path: str, record_count: int) -> str:
    """生成 manifest 指引文件到 manifests_openclaw/。"""
    os.makedirs(MANIFEST_OUT_DIR, exist_ok=True)
    ts = _now_iso().replace(":", "").replace("+", "_")
    job_id = f"{category}_{ts}"
    manifest = {
        "spec_version": "1.0",
        "job_id": job_id,
        "created_at": _now_iso(),
        "producer": {
            "system": "external_crawler",
            "module": "writeIn",
            "run_id": ts,
        },
        "data_category": category,
        "source_file": os.path.basename(data_path),
        "record_count": record_count,
        "checksum": {"staging_sha256": _sha256(data_path)},
        "status": "done",
    }
    manifest_path = os.path.join(MANIFEST_OUT_DIR, f"{job_id}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest_path


def _write_receipt(category: str, success: bool, record_count: int,
                   error: Optional[str], dry_run: bool) -> str:
    """生成入库回执。"""
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    ts = _now_iso().replace(":", "").replace("+", "_")
    receipt = {
        "job_type": "writeIn",
        "category": category,
        "success": success,
        "record_count": record_count,
        "error": error,
        "dry_run": dry_run,
        "created_at": _now_iso(),
    }
    receipt_path = os.path.join(RECEIPT_DIR, f"writeIn_{category}_{ts}.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    return receipt_path


def _count_records(category: str, data: Dict[str, Any]) -> int:
    """统计数据中的记录数。"""
    if category == "company":
        return 1
    if category == "stock_daily":
        return len(data.get("stock_daily", []))
    if category == "announcement":
        return len(data.get("raw_announcements", []))
    if category == "news":
        return len(data.get("news_raw", []))
    if category == "macro":
        return len(data.get("items", []))
    if category == "financial":
        count = 0
        for key in ("income_statements", "balance_sheets", "cashflow_statements",
                     "financial_metrics", "financial_notes", "business_segments"):
            count += len(data.get(key, []))
        return count
    return 0


# ---------------------------------------------------------------------------
# 各类别入库逻辑
# ---------------------------------------------------------------------------

def _ingest_company(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = IngestCompanyPackageRequest(
        company_master=data.get("company_master"),
        company_profile=data.get("company_profile"),
        industries=data.get("industries", []),
        company_industries=data.get("company_industries", []),
    )
    result = container.ingest.ingest_company_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_stock_daily(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = IngestFinancialPackageRequest(
        stock_daily=data.get("stock_daily", []),
    )
    result = container.ingest.ingest_financial_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_announcement(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = IngestAnnouncementPackageRequest(
        raw_announcements=data.get("raw_announcements", []),
        sync_vector_index=data.get("sync_vector_index", False),
    )
    result = container.ingest.ingest_announcement_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_news(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = IngestNewsPackageRequest(
        news_raw=data.get("news_raw", []),
        sync_vector_index=data.get("sync_vector_index", False),
    )
    result = container.ingest.ingest_news_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_macro(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = BatchItemsRequest(
        items=data.get("items", []),
    )
    result = container.macro_write.batch_upsert_macro_indicators(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_financial(data: Dict[str, Any]) -> Dict[str, Any]:
    container = get_container()
    req = IngestFinancialPackageRequest(
        income_statements=data.get("income_statements", []),
        balance_sheets=data.get("balance_sheets", []),
        cashflow_statements=data.get("cashflow_statements", []),
        financial_metrics=data.get("financial_metrics", []),
        financial_notes=data.get("financial_notes", []),
        business_segments=data.get("business_segments", []),
        sync_vector_index=data.get("sync_vector_index", False),
    )
    result = container.ingest.ingest_financial_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


INGEST_DISPATCH = {
    "company": _ingest_company,
    "stock_daily": _ingest_stock_daily,
    "announcement": _ingest_announcement,
    "news": _ingest_news,
    "macro": _ingest_macro,
    "financial": _ingest_financial,
}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(category: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    扫描 Data/ 目录，按文件名匹配类别并入库。

    Args:
        category: 若指定，只处理该类别。
        dry_run: 为 True 时只校验不入库。

    Returns:
        {"success": bool, "results": [...]}
    """
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"[INFO] Data directory created: {DATA_DIR}")
        print("[INFO] No data files found.")
        return {"success": True, "results": []}

    results: List[Dict[str, Any]] = []

    for filename, cat in FILE_CATEGORY_MAP.items():
        if category and cat != category:
            continue

        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        print(f"\n{'=' * 60}")
        print(f"[PROCESS] {filename} -> {cat}")
        print(f"{'=' * 60}")

        data = _load_json(filepath)
        if data is None:
            results.append({"category": cat, "file": filename,
                            "success": False, "error": "JSON parse failed"})
            continue

        record_count = _count_records(cat, data)
        print(f"  records: {record_count}")

        # 清理旧 manifest
        cleaned = _clean_old_manifests(cat)
        if cleaned:
            print(f"  cleaned {cleaned} old manifest(s)")

        if dry_run:
            print(f"  [DRY-RUN] would ingest {record_count} records for {cat}")
            results.append({"category": cat, "file": filename,
                            "success": True, "dry_run": True,
                            "record_count": record_count})
            continue

        # 入库
        ingest_fn = INGEST_DISPATCH.get(cat)
        if not ingest_fn:
            print(f"  [ERROR] no ingest function for {cat}")
            results.append({"category": cat, "file": filename,
                            "success": False, "error": "no ingest function"})
            continue

        try:
            outcome = ingest_fn(data)
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            _write_receipt(cat, False, record_count, str(exc), dry_run)
            results.append({"category": cat, "file": filename,
                            "success": False, "error": str(exc)})
            continue

        if outcome["success"]:
            print(f"  [DONE] {cat}: {outcome['data']}")
            manifest_path = _write_manifest(cat, filepath, record_count)
            print(f"  manifest: {manifest_path}")
            # 入库成功后删除源文件
            os.remove(filepath)
            print(f"  deleted: {filename}")
        else:
            print(f"  [FAIL] {cat}: {outcome['error']}")

        _write_receipt(cat, outcome["success"], record_count,
                       outcome.get("error"), dry_run)
        results.append({"category": cat, "file": filename,
                        "success": outcome["success"],
                        "record_count": record_count,
                        "error": outcome.get("error")})

    # 汇总
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    total = len(results)
    ok = sum(1 for r in results if r["success"])
    fail = total - ok
    for r in results:
        status = "OK" if r["success"] else "FAIL"
        print(f"  {r['category']:16s} [{status}] {r.get('record_count', '?')} records")
    print(f"total: {total}  ok: {ok}  fail: {fail}")
    print(f"{'=' * 60}")

    return {"success": fail == 0, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read JSON files from Data/ directory and ingest into database."
    )
    parser.add_argument(
        "--category",
        default=None,
        choices=list(set(FILE_CATEGORY_MAP.values())),
        help="Only process this category.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without actually ingesting.",
    )
    args = parser.parse_args()

    result = run(category=args.category, dry_run=args.dry_run)
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
