"""
ingest_center / openclaw_adapter.py
====================================

openclaw 统一 envelope 格式解包适配层。

职责：
    1. 扫描 openclaw_inbox/ 目录下 openclaw 爬虫投放的 JSON 文件
    2. 校验 envelope 顶层结构
    3. 按 payload_type 将 envelope 外层元数据合并进 payload（解包）
    4. 按 payload_type 分组批量调用 ServiceContainer 入库
    5. 入库成功后删除源文件，生成 manifest 和 receipt

envelope 格式：
    {
      "batch_id": "20260424_0001",
      "task_id": "crawl_med_001",
      "source": { "source_type", "source_name", "source_url", "source_category" },
      "entity": { "entity_type", "stock_code", "stock_name", "industry_code", "industry_name" },
      "document": { "doc_type", "title", "publish_time", "crawl_time", "file_hash", "raw_file_path", "language" },
      "payload_type": "announcement_raw | ...",
      "payload": { ... },
      "processing": { "parse_status", "parse_method", "confidence_score", "version_no" },
      "extra": {}
    }

用法：
    python -m ingest_center.openclaw_adapter
    python -m ingest_center.openclaw_adapter --dry-run
    python -m ingest_center.openclaw_adapter --payload-type announcement_raw
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

from . import common
from .service_runtime import get_container
from .id_resolver import resolve_news_id

from app.service.write_requests import (
    BatchItemsRequest,
    IngestAnnouncementPackageRequest,
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    IngestNewsPackageRequest,
    ReplaceNewsCompanyMapRequest,
)

INBOX_DIR = os.path.join(os.path.dirname(__file__), "openclaw_inbox")
RECEIPT_DIR = os.path.join(os.path.dirname(__file__), "receipts")
MANIFEST_OUT_DIR = os.path.join(os.path.dirname(__file__), "manifests_openclaw")

KNOWN_PAYLOAD_TYPES = {
    "announcement_raw",
    "announcement_structured",
    "news_raw",
    "news_structured",
    "news_company_map",
    "financial_statement",
    "financial_metric",
    "macro_indicator",
    "drug_event",
    "trial_event",
    "procurement_event",
    "regulatory_risk_event",
    "stock_daily",
    "company_profile",
}

FINANCIAL_STATEMENT_SUB_TYPES = {
    "income_statement": "income_statements",
    "balance_sheet": "balance_sheets",
    "cashflow_statement": "cashflow_statements",
}

# 各 payload_type 允许写入数据库的字段白名单（None 表示不过滤）
_ALLOWED_FIELDS: Dict[str, Optional[set]] = {
    "macro_indicator": {"indicator_name", "period", "value", "unit", "source_type", "source_url"},
    "announcement_raw": None,
    "news_raw": {"news_uid", "title", "publish_time", "source_name", "source_url",
                 "author_name", "content", "news_type", "language", "file_hash"},
    "stock_daily": {"stock_code", "trade_date", "open_price", "close_price",
                    "high_price", "low_price", "volume", "turnover", "source_type"},
    "financial_metric": {"stock_code", "report_date", "fiscal_year", "metric_name",
                         "metric_value", "metric_unit", "calc_method", "source_ref_json"},
}

# ---------------------------------------------------------------------------
# envelope 字段映射：envelope 路径 -> payload 目标字段
# payload 中已有的字段不会被覆盖
# ---------------------------------------------------------------------------

_DEFAULT_FIELD_MAP = {
    "entity.stock_code": "stock_code",
    "source.source_type": "source_type",
    "source.source_url": "source_url",
}

ENVELOPE_FIELD_MAP: Dict[str, Dict[str, str]] = {
    "announcement_raw": {
        "entity.stock_code": "stock_code",
        "document.title": "title",
        "document.publish_time": "publish_date",
        "document.file_hash": "file_hash",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "announcement_structured": {
        "entity.stock_code": "stock_code",
        "document.title": "title",
        "document.publish_time": "publish_date",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "news_raw": {
        "document.title": "title",
        "document.publish_time": "publish_time",
        "document.file_hash": "file_hash",
        "document.language": "language",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
        "source.source_name": "source_name",
    },
    "news_structured": {
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "news_company_map": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "financial_statement": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "financial_metric": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "stock_daily": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
    },
    "macro_indicator": {
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "drug_event": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "trial_event": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "procurement_event": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "regulatory_risk_event": {
        "entity.stock_code": "stock_code",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
    "company_profile": {
        "entity.stock_code": "stock_code",
        "entity.stock_name": "stock_name",
        "source.source_type": "source_type",
        "source.source_url": "source_url",
    },
}

# payload_type -> (service 属性, 方法名, Request 类, 填充字段名)
# service 属性为 None 时使用 container.ingest
DISPATCH_TABLE: Dict[str, Tuple[Optional[str], str, type, str]] = {
    "announcement_raw":        (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "raw_announcements"),
    "announcement_structured": (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "structured_announcements"),
    "drug_event":              (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "drug_approvals"),
    "trial_event":             (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "clinical_trials"),
    "procurement_event":       (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "procurement_events"),
    "regulatory_risk_event":   (None, "ingest_announcement_package", IngestAnnouncementPackageRequest, "regulatory_risks"),
    "news_raw":                (None, "ingest_news_package",         IngestNewsPackageRequest,          "news_raw"),
    "news_structured":         (None, "ingest_news_package",         IngestNewsPackageRequest,          "news_structured"),
    "financial_metric":        (None, "ingest_financial_package",     IngestFinancialPackageRequest,     "financial_metrics"),
    "stock_daily":             (None, "ingest_financial_package",     IngestFinancialPackageRequest,     "stock_daily"),
    "macro_indicator":         ("macro_write", "batch_upsert_macro_indicators", BatchItemsRequest, "items"),
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return common.now_iso()


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [ERROR] failed to load {path}: {exc}")
        return None


def _resolve_dotted(envelope: Dict[str, Any], dotted_key: str) -> Any:
    """从 envelope 中按点分路径取值，如 'entity.stock_code'。"""
    parts = dotted_key.split(".")
    obj = envelope
    for p in parts:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(p)
    return obj


# ---------------------------------------------------------------------------
# envelope 校验
# ---------------------------------------------------------------------------

def _validate_envelope(data: Dict[str, Any]) -> List[str]:
    errors = []
    for key in ("batch_id", "payload_type", "payload"):
        if key not in data:
            errors.append(f"missing required field: {key}")
    for key in ("source", "entity", "document"):
        if key not in data or not isinstance(data.get(key), dict):
            errors.append(f"missing or invalid field: {key}")
    pt = data.get("payload_type")
    if pt and pt not in KNOWN_PAYLOAD_TYPES:
        errors.append(f"unknown payload_type: {pt}")
    if not isinstance(data.get("payload"), dict):
        errors.append("payload must be a dict")
    return errors


# ---------------------------------------------------------------------------
# envelope 解包
# ---------------------------------------------------------------------------

# payload_type -> payload 内嵌列表字段名（openclaw 批量格式）
_BATCH_PAYLOAD_KEYS: Dict[str, str] = {
    "announcement_raw":      "raw_announcements",
    "announcement_structured": "structured_announcements",
    "news_raw":              "news_raw",
    "news_structured":       "news_structured",
    "stock_daily":           "stock_daily",
    "macro_indicator":       "macro_indicators",
    "financial_metric":      "financial_metrics",
    "drug_event":            "drug_approvals",
    "trial_event":           "clinical_trials",
    "procurement_event":     "procurement_events",
    "regulatory_risk_event": "regulatory_risks",
}


def _expand_envelope(envelope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    如果 payload 里包含嵌套列表（openclaw 批量格式），展开为多个 envelope。
    否则原样返回单元素列表。
    """
    pt = envelope["payload_type"]
    batch_key = _BATCH_PAYLOAD_KEYS.get(pt)
    if batch_key and isinstance(envelope["payload"].get(batch_key), list):
        rows = envelope["payload"][batch_key]
        result = []
        for row in rows:
            clone = {k: v for k, v in envelope.items() if k != "payload"}
            clone["payload"] = row
            result.append(clone)
        return result
    return [envelope]


def _unpack_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """将 envelope 外层元数据合并进 payload，返回扁平 dict。"""
    pt = envelope["payload_type"]
    item = dict(envelope["payload"])

    field_map = ENVELOPE_FIELD_MAP.get(pt, _DEFAULT_FIELD_MAP)
    for dotted_key, target_field in field_map.items():
        if target_field not in item:
            val = _resolve_dotted(envelope, dotted_key)
            if val is not None:
                item[target_field] = val

    # extra 中的字段也合并（如 fiscal_year, report_type, source_announcement_id）
    extra = envelope.get("extra")
    if isinstance(extra, dict):
        for k, v in extra.items():
            if k not in item and v is not None:
                item[k] = v

    # 按白名单过滤多余字段
    allowed = _ALLOWED_FIELDS.get(pt)
    if allowed is not None:
        item = {k: v for k, v in item.items() if k in allowed}

    return item


# ---------------------------------------------------------------------------
# 分组键
# ---------------------------------------------------------------------------

def _batch_key(envelope: Dict[str, Any], filepath: str) -> str:
    pt = envelope["payload_type"]
    if pt == "financial_statement":
        sub = envelope["payload"].get("statement_type", "unknown")
        return f"financial_statement:{sub}"
    # 不可批量的类型，每条独立
    if pt in ("company_profile", "news_company_map"):
        return f"{pt}::{filepath}"
    return pt


# ---------------------------------------------------------------------------
# service 调用
# ---------------------------------------------------------------------------

def _call_standard(batch_key: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """标准类型：查 DISPATCH_TABLE，构造 Request，调用 service。"""
    pt = batch_key.split("::")[0]

    # financial_statement 特殊路由
    if pt.startswith("financial_statement:"):
        sub_type = pt.split(":")[1]
        req_field = FINANCIAL_STATEMENT_SUB_TYPES.get(sub_type)
        if not req_field:
            return {"success": False, "data": None, "error": f"unknown statement_type: {sub_type}"}
        # 从 item 中移除 statement_type，它不是 ORM 字段
        clean_items = [{k: v for k, v in item.items() if k != "statement_type"} for item in items]
        req = IngestFinancialPackageRequest(**{req_field: clean_items})
        container = get_container()
        result = container.ingest.ingest_financial_package(req)
        return {"success": result.success, "data": result.data,
                "error": result.message if not result.success else None}

    entry = DISPATCH_TABLE.get(pt)
    if not entry:
        return {"success": False, "data": None, "error": f"no dispatch entry for: {pt}"}

    svc_attr, method_name, req_class, req_field = entry
    container = get_container()
    svc = getattr(container, svc_attr) if svc_attr else container.ingest
    method = getattr(svc, method_name)
    req = req_class(**{req_field: items})
    result = method(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _call_company_profile(item: Dict[str, Any]) -> Dict[str, Any]:
    """company_profile 特殊处理：拆分为 company_master + company_profile。"""
    master_fields = {
        "stock_code", "stock_name", "full_name", "exchange",
        "industry_level1", "industry_level2", "listing_date",
        "status", "alias_json", "source_type", "source_url",
    }
    profile_fields = {
        "stock_code", "business_summary", "core_products_json",
        "main_segments_json", "market_position", "management_summary",
    }

    company_master = {k: v for k, v in item.items() if k in master_fields}
    company_profile = {k: v for k, v in item.items() if k in profile_fields}

    # stock_code 必须在两边都有
    if "stock_code" in item:
        company_profile["stock_code"] = item["stock_code"]

    industries = item.get("industries", [])
    company_industries = item.get("company_industries", [])

    req = IngestCompanyPackageRequest(
        company_master=company_master if company_master.get("stock_code") else None,
        company_profile=company_profile if company_profile.get("stock_code") else None,
        industries=industries,
        company_industries=company_industries,
    )
    container = get_container()
    result = container.ingest.ingest_company_package(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _call_news_company_map(item: Dict[str, Any]) -> Dict[str, Any]:
    """news_company_map 特殊处理：反查 news_id，调用 replace。"""
    news_uid = item.get("news_uid")
    news_id = item.get("news_id")

    if news_id is None and news_uid:
        news_id = resolve_news_id(news_uid=str(news_uid))
    if news_id is None:
        return {"success": False, "data": None,
                "error": f"cannot resolve news_id for news_uid={news_uid!r}"}

    map_item = {k: v for k, v in item.items() if k not in ("news_uid", "news_id")}
    req = ReplaceNewsCompanyMapRequest(news_id=int(news_id), items=[map_item])
    container = get_container()
    result = container.news_write.replace_news_company_map(req)
    return {"success": result.success, "data": result.data,
            "error": result.message if not result.success else None}


def _ingest_group(batch_key: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据 batch_key 分发到对应的 service 调用。"""
    pt = batch_key.split("::")[0]

    try:
        if pt == "company_profile" or batch_key.startswith("company_profile::"):
            return _call_company_profile(items[0])
        if pt == "news_company_map" or batch_key.startswith("news_company_map::"):
            return _call_news_company_map(items[0])
        return _call_standard(batch_key, items)
    except Exception as exc:
        tb = traceback.format_exc()
        if len(tb) > 2000:
            tb = tb[:2000] + "\n... (truncated)"
        print(f"  [EXCEPTION] {exc}")
        return {"success": False, "data": None, "error": f"[{type(exc).__name__}] {exc}"}


# ---------------------------------------------------------------------------
# receipt / manifest
# ---------------------------------------------------------------------------

def _write_receipt(batch_key: str, success: bool, record_count: int,
                   error: Optional[str], dry_run: bool,
                   source_files: List[str]) -> str:
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    ts = _now_iso().replace(":", "").replace("+", "_")
    safe_key = batch_key.replace("::", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
    receipt = {
        "job_type": "openclaw_adapter",
        "batch_key": batch_key,
        "success": success,
        "record_count": record_count,
        "error": error,
        "dry_run": dry_run,
        "source_files": [os.path.basename(f) for f in source_files],
        "created_at": _now_iso(),
    }
    path = os.path.join(RECEIPT_DIR, f"openclaw_{safe_key}_{ts}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    return path


def _write_manifest(batch_key: str, source_files: List[str], record_count: int) -> str:
    os.makedirs(MANIFEST_OUT_DIR, exist_ok=True)
    ts = _now_iso().replace(":", "").replace("+", "_")
    safe_key = batch_key.replace("::", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
    manifest = {
        "spec_version": "1.0",
        "job_id": f"openclaw_{safe_key}_{ts}",
        "created_at": _now_iso(),
        "producer": {
            "system": "openclaw",
            "module": "openclaw_adapter",
            "run_id": ts,
        },
        "data_category": batch_key.split("::")[0],
        "record_count": record_count,
        "source_files": [os.path.basename(f) for f in source_files],
        "status": "done",
    }
    path = os.path.join(MANIFEST_OUT_DIR, f"openclaw_{safe_key}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(
    payload_type: Optional[str] = None,
    dry_run: bool = False,
    inbox_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    扫描 openclaw_inbox/ 目录，解包 envelope 并入库。

    Args:
        payload_type: 若指定，只处理该 payload_type。
        dry_run: 为 True 时只校验不入库。
        inbox_dir: 自定义收件目录。

    Returns:
        {"success": bool, "results": [...]}
    """
    inbox = inbox_dir or INBOX_DIR
    if not os.path.isdir(inbox):
        os.makedirs(inbox, exist_ok=True)
        print(f"[INFO] inbox directory created: {inbox}")
        print("[INFO] no envelope files found.")
        return {"success": True, "results": []}

    files = sorted(glob.glob(os.path.join(inbox, "*.json")))
    if not files:
        print("[INFO] no envelope files found in inbox.")
        return {"success": True, "results": []}

    print(f"[SCAN] found {len(files)} file(s) in {inbox}")

    # 阶段 1：解析、校验、解包、分组
    groups: Dict[str, List[Tuple[Dict[str, Any], str]]] = {}
    skipped = 0

    for filepath in files:
        data = _load_json(filepath)
        if data is None:
            skipped += 1
            continue

        errors = _validate_envelope(data)
        if errors:
            print(f"  [SKIP] {os.path.basename(filepath)}: {'; '.join(errors)}")
            skipped += 1
            continue

        pt = data["payload_type"]
        if payload_type and pt != payload_type:
            continue

        expanded = _expand_envelope(data)
        for env in expanded:
            item = _unpack_envelope(env)
            key = _batch_key(env, filepath)
            if key not in groups:
                groups[key] = []
            groups[key].append((item, filepath))

    if not groups:
        print("[INFO] no valid envelopes to process.")
        return {"success": True, "results": []}

    print(f"[GROUP] {len(groups)} group(s), {skipped} skipped")
    for key, entries in groups.items():
        print(f"  {key}: {len(entries)} item(s)")

    # 阶段 2：逐组入库
    results: List[Dict[str, Any]] = []

    for key, entries in groups.items():
        items = [e[0] for e in entries]
        source_files = [e[1] for e in entries]
        pt_display = key.split("::")[0]

        print(f"\n{'=' * 60}")
        print(f"[INGEST] {pt_display} ({len(items)} item(s))")
        print(f"{'=' * 60}")

        if dry_run:
            print(f"  [DRY-RUN] would ingest {len(items)} item(s) for {pt_display}")
            _write_receipt(key, True, len(items), None, True, source_files)
            results.append({"batch_key": key, "success": True, "dry_run": True,
                            "record_count": len(items)})
            continue

        outcome = _ingest_group(key, items)

        if outcome["success"]:
            print(f"  [DONE] {pt_display}: {outcome['data']}")
            manifest_path = _write_manifest(key, source_files, len(items))
            print(f"  manifest: {manifest_path}")
            for fp in set(source_files):
                if os.path.exists(fp):
                    os.remove(fp)
                    print(f"  deleted: {os.path.basename(fp)}")
        else:
            print(f"  [FAIL] {pt_display}: {outcome['error']}")

        receipt_path = _write_receipt(key, outcome["success"], len(items),
                                      outcome.get("error"), False, source_files)
        print(f"  receipt: {receipt_path}")

        results.append({"batch_key": key, "success": outcome["success"],
                        "record_count": len(items), "error": outcome.get("error")})

    # 汇总
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    total = len(results)
    ok = sum(1 for r in results if r["success"])
    fail = total - ok
    for r in results:
        status = "OK" if r["success"] else "FAIL"
        print(f"  {r['batch_key']:40s} [{status}] {r.get('record_count', '?')} item(s)")
    print(f"total: {total}  ok: {ok}  fail: {fail}  skipped: {skipped}")
    print(f"{'=' * 60}")

    return {"success": fail == 0, "results": results}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unpack openclaw envelope JSON files and ingest into database."
    )
    parser.add_argument(
        "--payload-type",
        default=None,
        choices=sorted(KNOWN_PAYLOAD_TYPES),
        help="Only process envelopes of this payload_type.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and group envelopes without calling service.",
    )
    parser.add_argument(
        "--inbox-dir",
        default=None,
        help=f"Override inbox directory. Default: {INBOX_DIR}",
    )
    args = parser.parse_args()

    result = run(
        payload_type=args.payload_type,
        dry_run=args.dry_run,
        inbox_dir=args.inbox_dir,
    )
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
