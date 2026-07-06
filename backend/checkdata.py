"""OpenClaw batch data validator.

This module is intentionally independent from the database layer.  It validates
the batch files before import_batch.py writes anything, so a malformed package
can be returned to OpenClaw/AI for repair as a whole.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SUPPORTED_TYPES = {
    "company",
    "financial",
    "announcement",
    "research_report",
    "news",
    "macro",
    "pipeline_drug",
}

DEFAULT_FILES = {
    "company": "company/company_records.jsonl",
    "financial": "financial/financial_records.jsonl",
    "announcement": "announcement/announcement_records.jsonl",
    "research_report": "research_report/research_report_records.jsonl",
    "news": "news/news_records.jsonl",
    "macro": "macro/macro_records.jsonl",
    "pipeline_drug": "pipeline/pipeline_drug_records.jsonl",
}

TABLE_ORDER = [
    "company",
    "financial",
    "announcement",
    "research_report",
    "news",
    "macro",
    "pipeline_drug",
]

# Full daily packages must include core data families. Macro is optional: if it
# is present we validate it, but missing macro does not block the package.
REQUIRED_DATA_TYPES = set(TABLE_ORDER) - {"macro"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STOCK_CODE_RE = re.compile(r"^\d{6}$")

REPORT_TYPES = {"annual", "q1", "q2", "q3", "daily"}
FINANCIAL_REPORT_TYPES = {"annual", "q1", "q2", "q3"}
EXCHANGES = {"SH", "SZ", "BJ", "HK"}
SCOPE_TYPES = {"company", "industry"}
TRIAL_PHASES = {
    "preclinical",
    "phase1",
    "phase1_2",
    "phase2",
    "phase2_3",
    "phase3",
    "nda",
    "nda_rejected",
    "approved",
    "terminated",
    "withdrawn",
    "unknown",
}

NUMERIC_FIELDS = {
    "financial": {
        "fiscal_year",
        "revenue",
        "operating_cost",
        "gross_profit",
        "gross_margin",
        "selling_expense",
        "admin_expense",
        "rd_expense",
        "rd_ratio",
        "operating_profit",
        "net_profit",
        "net_profit_deducted",
        "eps",
        "total_assets",
        "total_liabilities",
        "debt_ratio",
        "operating_cashflow",
        "investing_cashflow",
        "financing_cashflow",
        "open_price",
        "close_price",
        "high_price",
        "low_price",
        "volume",
        "amount",
        "change_pct",
    },
    "macro": {"value"},
    "pipeline_drug": {"confidence_score"},
}

COMMON_DATE_FIELDS = {
    "company": ["listing_date"],
    "financial": ["report_date", "trade_date"],
    "announcement": ["publish_date"],
    "research_report": ["publish_date"],
    "macro": ["period_date"],
}


def validate_batch(batch_dir: str | Path) -> dict[str, Any]:
    """Validate one incoming batch directory and return a repair-friendly report."""
    batch_path = Path(batch_dir)
    report = _new_report(batch_path.name)

    manifest = _load_manifest(batch_path, report)
    if manifest is None:
        _finish_report(report)
        return report

    batch_id = manifest.get("batch_id") or batch_path.name
    report["batch_id"] = batch_id

    _validate_manifest(batch_path, manifest, report)
    if report["errors"]:
        _finish_report(report)
        return report

    files_map = manifest.get("files") or {}
    data_types = manifest.get("data_types") or []
    record_counts: dict[str, int] = {data_type: 0 for data_type in TABLE_ORDER}
    financial_daily_count = 0

    for data_type in TABLE_ORDER:
        if data_type not in data_types:
            continue
        rel_path = files_map.get(data_type) or DEFAULT_FILES.get(data_type)
        jsonl_path = batch_path / rel_path
        records = _read_jsonl(jsonl_path, data_type, rel_path, report)
        record_counts[data_type] = len(records)
        for row_no, record in records:
            if data_type == "financial" and record.get("report_type") == "daily":
                financial_daily_count += 1
            report["summary"]["total_records"] += 1
            before = len(report["errors"])
            _validate_record(data_type, record, row_no, rel_path, report)
            if len(report["errors"]) == before:
                report["summary"]["valid_records"] += 1
            else:
                report["summary"]["invalid_records"] += 1

    _validate_batch_completeness(manifest, record_counts, financial_daily_count, report)
    _finish_report(report)
    return report


def _new_report(batch_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "validation_failed",
        "batch_id": batch_id,
        "summary": {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "error_count": 0,
        },
        "errors": [],
    }


def _finish_report(report: dict[str, Any]) -> None:
    report["summary"]["error_count"] = len(report["errors"])
    report["ok"] = len(report["errors"]) == 0
    report["status"] = "success" if report["ok"] else "validation_failed"


def _load_manifest(batch_path: Path, report: dict[str, Any]) -> dict[str, Any] | None:
    manifest_path = batch_path / "manifest.json"
    if not manifest_path.exists():
        _add_error(
            report,
            data_type="manifest",
            file="manifest.json",
            row=None,
            field="manifest.json",
            value=None,
            reason="缺少 manifest.json",
            expected="data/incoming/{batch_id}/manifest.json 必须存在",
            suggestion="请重新生成批次目录，并在根目录放置 manifest.json。",
        )
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8-sig") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        _add_error(
            report,
            data_type="manifest",
            file="manifest.json",
            row=exc.lineno,
            field="manifest.json",
            value=None,
            reason=f"manifest.json 不是合法 JSON：{exc.msg}",
            expected="合法 JSON 对象",
            suggestion="请修复 manifest.json 的 JSON 语法后重试。",
        )
        return None
    except OSError as exc:
        _add_error(
            report,
            data_type="manifest",
            file="manifest.json",
            row=None,
            field="manifest.json",
            value=None,
            reason=f"读取 manifest.json 失败：{exc}",
            expected="文件可读取",
            suggestion="请检查文件权限和路径。",
        )
        return None
    if not isinstance(manifest, dict):
        _add_error(
            report,
            data_type="manifest",
            file="manifest.json",
            row=None,
            field="manifest.json",
            value=manifest,
            reason="manifest.json 顶层必须是 JSON 对象",
            expected='{"batch_id": "...", "status": "ready", "data_types": [...], "files": {...}}',
            suggestion="请按入库手册重建 manifest.json。",
        )
        return None
    return manifest


def _validate_manifest(batch_path: Path, manifest: dict[str, Any], report: dict[str, Any]) -> None:
    _require_field(manifest, "batch_id", "manifest", None, "manifest.json", report)
    _require_field(manifest, "status", "manifest", None, "manifest.json", report)
    _require_field(manifest, "data_types", "manifest", None, "manifest.json", report)
    _require_field(manifest, "files", "manifest", None, "manifest.json", report)

    if manifest.get("status") != "ready":
        _add_error(
            report,
            "manifest",
            "manifest.json",
            None,
            "status",
            manifest.get("status"),
            "manifest.status 必须为 ready",
            '"ready"',
            '请将 status 改为 "ready" 后再提交。',
        )

    data_types = manifest.get("data_types")
    if not isinstance(data_types, list) or not data_types:
        _add_error(
            report,
            "manifest",
            "manifest.json",
            None,
            "data_types",
            data_types,
            "data_types 必须是非空数组",
            '例如 ["company", "financial"]',
            "请只列出本批次实际包含的数据类型。",
        )
        data_types = []

    files = manifest.get("files")
    if not isinstance(files, dict):
        _add_error(
            report,
            "manifest",
            "manifest.json",
            None,
            "files",
            files,
            "files 必须是对象，映射 data_type 到 JSONL 相对路径",
            '例如 {"company": "company/company_records.jsonl"}',
            "请为每个 data_type 填写对应 JSONL 文件路径。",
        )
        files = {}

    seen = set()
    for data_type in data_types:
        if data_type in seen:
            _add_error(
                report,
                "manifest",
                "manifest.json",
                None,
                "data_types",
                data_type,
                "data_types 中存在重复类型",
                "每种 data_type 只能出现一次",
                "请删除重复 data_type。",
            )
        seen.add(data_type)
        if data_type not in SUPPORTED_TYPES:
            _add_error(
                report,
                "manifest",
                "manifest.json",
                None,
                "data_types",
                data_type,
                "未知 data_type",
                "/".join(TABLE_ORDER),
                "请改为入库手册支持的数据类型。",
            )
            continue
        rel_path = files.get(data_type) or DEFAULT_FILES.get(data_type)
        if not rel_path:
            _add_error(
                report,
                "manifest",
                "manifest.json",
                None,
                f"files.{data_type}",
                rel_path,
                "缺少该 data_type 对应的 JSONL 路径",
                DEFAULT_FILES.get(data_type),
                "请在 files 中补充相对路径。",
            )
            continue
        if Path(str(rel_path)).is_absolute() or ".." in Path(str(rel_path)).parts:
            _add_error(
                report,
                "manifest",
                "manifest.json",
                None,
                f"files.{data_type}",
                rel_path,
                "JSONL 路径必须是批次目录内的相对路径",
                "不允许绝对路径或 ..",
                "请改成批次目录内的相对路径。",
            )
            continue
        if not (batch_path / rel_path).exists():
            _add_error(
                report,
                data_type,
                str(rel_path),
                None,
                f"files.{data_type}",
                rel_path,
                "manifest 声明的 JSONL 文件不存在",
                "文件必须存在",
                "请生成该 JSONL 文件，或从 data_types/files 中移除该类型。",
            )


def _validate_batch_completeness(
    manifest: dict[str, Any],
    record_counts: dict[str, int],
    financial_daily_count: int,
    report: dict[str, Any],
) -> None:
    """Validate package-level data coverage required by the handbook."""
    data_types = set(manifest.get("data_types") or [])
    files = manifest.get("files") or {}

    for data_type in TABLE_ORDER:
        if data_type not in REQUIRED_DATA_TYPES:
            continue
        if data_type not in data_types:
            _add_error(
                report,
                data_type,
                "manifest.json",
                None,
                "data_types",
                sorted(data_types),
                f"批次缺少必爬数据类型：{data_type}",
                "company/financial/announcement/research_report/news/pipeline_drug 必须齐全；macro 可选",
                f"请让 OpenClaw 补爬 {data_type}，并在 manifest.data_types 与 files 中声明。",
            )
            continue
        if data_type not in files and data_type in DEFAULT_FILES:
            _add_error(
                report,
                data_type,
                "manifest.json",
                None,
                f"files.{data_type}",
                None,
                f"批次缺少 {data_type} 对应文件声明",
                DEFAULT_FILES[data_type],
                f"请在 manifest.files 中补充 {data_type} 的 JSONL 路径。",
            )
            continue
        if record_counts.get(data_type, 0) <= 0:
            _add_error(
                report,
                data_type,
                str(files.get(data_type) or DEFAULT_FILES.get(data_type) or "manifest.json"),
                None,
                data_type,
                record_counts.get(data_type, 0),
                f"必爬数据类型 {data_type} 没有任何记录",
                "每个必爬 data_type 至少 1 条记录",
                f"请让 OpenClaw 补爬 {data_type} 数据；如果确认没有数据，也需要提供可解释的占位/说明机制后再放行。",
            )

    if record_counts.get("financial", 0) > 0 and financial_daily_count <= 0:
        _add_error(
            report,
            "financial",
            str(files.get("financial") or DEFAULT_FILES["financial"]),
            None,
            "report_type",
            None,
            "financial 中缺少 daily 日行情记录",
            "financial_records.jsonl 至少包含一条 report_type='daily' 的日行情数据",
            "请让 OpenClaw 补爬日 K/日行情数据，并写为 report_type='daily'。",
        )

    if record_counts.get("pipeline_drug", 0) <= 0:
        _add_error(
            report,
            "pipeline_drug",
            str(files.get("pipeline_drug") or DEFAULT_FILES["pipeline_drug"]),
            None,
            "pipeline_drug",
            record_counts.get("pipeline_drug", 0),
            "缺少 pipeline_drug 管线数据",
            "pipeline/pipeline_drug_records.jsonl 至少 1 条记录",
            "请让 OpenClaw 补爬药品研发管线数据。",
        )


def _read_jsonl(
    path: Path,
    data_type: str,
    rel_path: str,
    report: dict[str, Any],
) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for row_no, line in enumerate(f, 1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError as exc:
                    _add_error(
                        report,
                        data_type,
                        rel_path,
                        row_no,
                        "__json__",
                        raw[:200],
                        f"JSONL 第 {row_no} 行不是合法 JSON：{exc.msg}",
                        "每行一个完整 JSON 对象",
                        "请修复该行 JSON 语法，不能跨行。",
                    )
                    continue
                if not isinstance(item, dict):
                    _add_error(
                        report,
                        data_type,
                        rel_path,
                        row_no,
                        "__json__",
                        item,
                        "JSONL 每行必须是 JSON 对象",
                        '{"field": "value"}',
                        "请把该行改成对象格式。",
                    )
                    continue
                records.append((row_no, item))
    except OSError as exc:
        _add_error(
            report,
            data_type,
            rel_path,
            None,
            "__file__",
            None,
            f"读取 JSONL 文件失败：{exc}",
            "文件可读取",
            "请检查文件权限和路径。",
        )
    return records


def _validate_record(
    data_type: str,
    item: dict[str, Any],
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    if data_type == "company":
        _validate_company(item, row, file, report)
    elif data_type == "financial":
        _validate_financial(item, row, file, report)
    elif data_type == "announcement":
        _validate_announcement(item, row, file, report)
    elif data_type == "research_report":
        _validate_research_report(item, row, file, report)
    elif data_type == "news":
        _validate_news(item, row, file, report)
    elif data_type == "macro":
        _validate_macro(item, row, file, report)
    elif data_type == "pipeline_drug":
        _validate_pipeline_drug(item, row, file, report)


def _validate_company(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "company"
    required = ["stock_code", "stock_name", "full_name", "exchange", "industry_level2", "business_summary"]
    _require_fields(item, required, data_type, row, file, report)
    _check_stock_code(item, "stock_code", data_type, row, file, report)
    _check_enum(item, "exchange", EXCHANGES, data_type, row, file, report)
    _check_date_fields(item, data_type, row, file, report)
    _check_string_length(item, "stock_name", 64, data_type, row, file, report)
    _check_string_length(item, "full_name", 128, data_type, row, file, report)
    _check_string_length(item, "industry_level2", 64, data_type, row, file, report)
    _check_json_type(item, "core_products_json", list, "数组", data_type, row, file, report, required=False)
    _check_json_type(item, "main_segments_json", dict, "对象", data_type, row, file, report, required=False)


def _validate_financial(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "financial"
    common_required = ["stock_code", "report_date", "report_type", "source_url"]
    _require_fields(item, common_required, data_type, row, file, report)
    _check_stock_code(item, "stock_code", data_type, row, file, report)
    _check_date_fields(item, data_type, row, file, report)
    _check_url(item, "source_url", data_type, row, file, report)
    _check_enum(item, "report_type", REPORT_TYPES, data_type, row, file, report)
    _check_numeric_fields(item, data_type, row, file, report)

    report_type = item.get("report_type")
    if report_type == "daily":
        required = [
            "trade_date",
            "open_price",
            "close_price",
            "high_price",
            "low_price",
            "volume",
            "amount",
            "change_pct",
        ]
        _require_fields(item, required, data_type, row, file, report)
        if item.get("report_date") and item.get("trade_date") and item.get("report_date") != item.get("trade_date"):
            _add_error(
                report,
                data_type,
                file,
                row,
                "report_date/trade_date",
                {"report_date": item.get("report_date"), "trade_date": item.get("trade_date")},
                "daily 日行情的 report_date 必须等于 trade_date",
                "report_date == trade_date",
                "请把 daily 行情的 report_date 和 trade_date 调整为同一交易日。",
            )
        change_pct = _to_decimal(item.get("change_pct"))
        if change_pct is not None and abs(change_pct) > Decimal("1"):
            _add_error(
                report,
                data_type,
                file,
                row,
                "change_pct",
                item.get("change_pct"),
                "change_pct 必须使用小数形式，不能使用百分数口径",
                "例如 1.21% 应写为 0.0121",
                "请把百分数除以 100 后再提交。",
            )
    elif report_type in FINANCIAL_REPORT_TYPES:
        required = [
            "revenue",
            "operating_cost",
            "operating_profit",
            "net_profit",
            "net_profit_deducted",
            "eps",
            "total_assets",
            "total_liabilities",
            "operating_cashflow",
            "investing_cashflow",
            "financing_cashflow",
        ]
        _require_fields(item, required, data_type, row, file, report)


def _validate_announcement(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "announcement"
    required = [
        "stock_code",
        "title",
        "publish_date",
        "announcement_type",
        "content",
        "summary_text",
        "source_url",
    ]
    _require_fields(item, required, data_type, row, file, report)
    _check_stock_code(item, "stock_code", data_type, row, file, report)
    _check_date_fields(item, data_type, row, file, report)
    _check_url(item, "source_url", data_type, row, file, report)
    _check_string_length(item, "title", 255, data_type, row, file, report)
    _check_string_length(item, "announcement_type", 64, data_type, row, file, report)
    _check_text_length(item, "content", 10000, data_type, row, file, report)
    _check_json_type(item, "key_fields_json", dict, "对象", data_type, row, file, report, required=False)


def _validate_research_report(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "research_report"
    required = ["scope_type", "title", "publish_date", "report_org", "content", "summary_text", "source_type"]
    _require_fields(item, required, data_type, row, file, report)
    _check_enum(item, "scope_type", SCOPE_TYPES, data_type, row, file, report)
    _check_date_fields(item, data_type, row, file, report)
    _check_string_length(item, "title", 255, data_type, row, file, report)
    _check_string_length(item, "report_org", 128, data_type, row, file, report)
    _check_text_length(item, "content", 10000, data_type, row, file, report)
    if item.get("scope_type") == "company":
        _require_field(item, "stock_code", data_type, row, file, report, reason="scope_type=company 时 stock_code 必填")
        _check_stock_code(item, "stock_code", data_type, row, file, report)
    if item.get("scope_type") == "industry":
        _require_field(item, "industry_code", data_type, row, file, report, reason="scope_type=industry 时 industry_code 必填")
    if not _is_empty(item.get("source_url")):
        _check_url(item, "source_url", data_type, row, file, report)


def _validate_news(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "news"
    required = [
        "title",
        "publish_time",
        "source_name",
        "source_url",
        "news_type",
        "content",
        "summary_text",
        "related_stock_codes_json",
    ]
    _require_fields(item, required, data_type, row, file, report)
    _check_datetime(item, "publish_time", data_type, row, file, report, require_time=True)
    _check_url(item, "source_url", data_type, row, file, report)
    _check_string_length(item, "title", 255, data_type, row, file, report)
    _check_string_length(item, "source_name", 128, data_type, row, file, report)
    _check_string_length(item, "news_type", 64, data_type, row, file, report)
    _check_text_length(item, "content", 10000, data_type, row, file, report)
    _check_json_type(item, "related_stock_codes_json", list, "数组", data_type, row, file, report, required=True)
    _check_json_type(item, "related_industry_codes_json", list, "数组", data_type, row, file, report, required=False)
    _check_json_type(item, "key_fields_json", dict, "对象", data_type, row, file, report, required=False)
    codes = item.get("related_stock_codes_json")
    if isinstance(codes, list):
        for index, code in enumerate(codes):
            if not isinstance(code, str) or not STOCK_CODE_RE.match(code):
                _add_error(
                    report,
                    data_type,
                    file,
                    row,
                    f"related_stock_codes_json[{index}]",
                    code,
                    "相关股票代码必须是 6 位数字字符串",
                    "例如 600276",
                    "请修正 related_stock_codes_json 中的股票代码。",
                )


def _validate_macro(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "macro"
    required = ["indicator_name", "period", "period_date", "value", "unit", "category"]
    _require_fields(item, required, data_type, row, file, report)
    _check_date_fields(item, data_type, row, file, report)
    _check_numeric_fields(item, data_type, row, file, report)
    _check_string_length(item, "indicator_name", 128, data_type, row, file, report)
    _check_string_length(item, "period", 32, data_type, row, file, report)
    _check_string_length(item, "unit", 32, data_type, row, file, report)
    _check_string_length(item, "category", 64, data_type, row, file, report)


def _validate_pipeline_drug(item: dict[str, Any], row: int, file: str, report: dict[str, Any]) -> None:
    data_type = "pipeline_drug"
    required = ["stock_code", "drug_name", "trial_phase", "evidence_text"]
    _require_fields(item, required, data_type, row, file, report)
    _check_stock_code(item, "stock_code", data_type, row, file, report)
    _check_enum(item, "trial_phase", TRIAL_PHASES, data_type, row, file, report)
    _check_numeric_fields(item, data_type, row, file, report)
    _check_json_type(item, "aliases", list, "数组", data_type, row, file, report, required=False)
    evidence = item.get("evidence_text")
    if isinstance(evidence, str) and len(evidence.strip()) < 20:
        _add_error(
            report,
            data_type,
            file,
            row,
            "evidence_text",
            evidence,
            "evidence_text 过短，无法支撑管线事实",
            "不少于 20 个字符",
            "请补充原文证据片段。",
        )
    combined_text = " ".join(str(item.get(k, "")) for k in ["trial_phase_raw", "evidence_text", "source_type"])
    if "IND" in combined_text.upper() and item.get("trial_phase") == "nda":
        _add_error(
            report,
            data_type,
            file,
            row,
            "trial_phase",
            item.get("trial_phase"),
            "IND 获批不能标记为 nda，nda 表示上市申请阶段",
            "preclinical 或 phase1",
            "请根据原文把 IND 事件映射为 preclinical 或 phase1。",
        )


def _require_fields(
    item: dict[str, Any],
    fields: list[str],
    data_type: str,
    row: int | None,
    file: str,
    report: dict[str, Any],
) -> None:
    for field in fields:
        _require_field(item, field, data_type, row, file, report)


def _require_field(
    item: dict[str, Any],
    field: str,
    data_type: str,
    row: int | None,
    file: str,
    report: dict[str, Any],
    *,
    reason: str | None = None,
) -> None:
    if _is_empty(item.get(field)):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            item.get(field),
            reason or "必填字段缺失或为空",
            "字段必须存在且不能为 null、空字符串、空数组或空对象",
            f"请补充 {field} 字段。",
        )


def _check_stock_code(
    item: dict[str, Any],
    field: str,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if not isinstance(value, str) or not STOCK_CODE_RE.match(value):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "股票代码格式错误",
            "A 股 6 位数字字符串，例如 600276",
            "请把 stock_code 修正为 6 位数字字符串。",
        )


def _check_date_fields(item: dict[str, Any], data_type: str, row: int, file: str, report: dict[str, Any]) -> None:
    for field in COMMON_DATE_FIELDS.get(data_type, []):
        if _is_empty(item.get(field)):
            continue
        _check_date(item, field, data_type, row, file, report)


def _check_date(
    item: dict[str, Any],
    field: str,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if isinstance(value, date) and not isinstance(value, datetime):
        return
    if not isinstance(value, str) or not DATE_RE.match(value):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "日期格式错误",
            "YYYY-MM-DD",
            f"请把 {field} 改成 YYYY-MM-DD 格式。",
        )
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "日期不是有效日历日期",
            "YYYY-MM-DD，例如 2026-05-27",
            f"请修正 {field} 的日期值。",
        )


def _check_datetime(
    item: dict[str, Any],
    field: str,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
    *,
    require_time: bool = False,
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if not isinstance(value, str):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "时间字段必须是字符串",
            "YYYY-MM-DDTHH:MM:SS",
            f"请把 {field} 改成 ISO 8601 字符串。",
        )
        return
    if require_time and "T" not in value:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "时间字段必须包含时分秒，不能只写日期",
            "YYYY-MM-DDTHH:MM:SS，例如 2026-05-20T00:00:00",
            f"如果只有日期，请把 {field} 补成 T00:00:00。",
        )
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "时间格式错误",
            "YYYY-MM-DDTHH:MM:SS",
            f"请把 {field} 改成合法 ISO 8601 时间。",
        )


def _check_url(
    item: dict[str, Any],
    field: str,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if not isinstance(value, str):
        _add_error(report, data_type, file, row, field, value, "URL 必须是字符串", "http(s) URL", f"请修正 {field}。")
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "URL 格式错误",
            "必须以 http:// 或 https:// 开头，并包含域名",
            f"请提供有效的 {field}。",
        )


def _check_enum(
    item: dict[str, Any],
    field: str,
    allowed: set[str],
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if value not in allowed:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "枚举值非法",
            "/".join(sorted(allowed)),
            f"请把 {field} 改为允许值之一。",
        )


def _check_numeric_fields(item: dict[str, Any], data_type: str, row: int, file: str, report: dict[str, Any]) -> None:
    for field in NUMERIC_FIELDS.get(data_type, set()):
        if _is_empty(item.get(field)):
            continue
        if _to_decimal(item.get(field)) is None:
            _add_error(
                report,
                data_type,
                file,
                row,
                field,
                item.get(field),
                "数值字段格式错误",
                "整数或小数，不能是文本、百分号或布尔值",
                f"请把 {field} 改成数字。",
            )


def _check_json_type(
    item: dict[str, Any],
    field: str,
    expected_type: type,
    expected_name: str,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
    *,
    required: bool,
) -> None:
    value = item.get(field)
    if _is_empty(value):
        if required:
            _require_field(item, field, data_type, row, file, report)
        return
    if not isinstance(value, expected_type):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            f"{field} 类型错误",
            f"JSON {expected_name}",
            f"请把 {field} 改成 JSON {expected_name}。",
        )


def _check_string_length(
    item: dict[str, Any],
    field: str,
    max_len: int,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if not isinstance(value, str):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value,
            "字符串字段类型错误",
            f"字符串，最长 {max_len} 字符",
            f"请把 {field} 改成字符串。",
        )
        return
    if len(value) > max_len:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            value[:200],
            f"字符串长度超过限制：{len(value)} > {max_len}",
            f"最长 {max_len} 字符",
            f"请缩短 {field}。",
        )


def _check_text_length(
    item: dict[str, Any],
    field: str,
    max_len: int,
    data_type: str,
    row: int,
    file: str,
    report: dict[str, Any],
) -> None:
    value = item.get(field)
    if _is_empty(value):
        return
    if not isinstance(value, str):
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            type(value).__name__,
            "长文本字段必须是字符串",
            f"字符串，最长 {max_len} 字符",
            f"请把 {field} 改成字符串。",
        )
        return
    if len(value) > max_len:
        _add_error(
            report,
            data_type,
            file,
            row,
            field,
            f"length={len(value)}",
            f"{field} 超过 {max_len} 字符",
            f"≤ {max_len} 字符；超过时应先总结再截断",
            "请先总结长文本，再保留关键内容到 10000 字以内，不能直接粗暴截前 10000 字。",
        )


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str) and value.strip():
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_json_safe(v) for v in value[:20]]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in list(value.items())[:20]}
    return str(value)


def _add_error(
    report: dict[str, Any],
    data_type: str,
    file: str,
    row: int | None,
    field: str,
    value: Any,
    reason: str,
    expected: str,
    suggestion: str,
) -> None:
    report["errors"].append(
        {
            "data_type": data_type,
            "file": file,
            "row": row,
            "field": field,
            "value": _json_safe(value),
            "reason": reason,
            "expected": expected,
            "suggestion": suggestion,
        }
    )


__all__ = ["validate_batch"]
