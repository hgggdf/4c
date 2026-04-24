"""
ingest_center / run_one.py
=========================

单任务入库入口模块。

职责：
    以单个 manifest 文件为粒度，执行完整的入库闭环流程：
    1. 读取并解析 manifest
    2. manifest 合法性校验
    3. 文件存在性与 sha256 校验
    4. 加载 staging 数据
    5. 提取并校验 records
    6. 构造 payload
    7. endpoint 一致性校验（仅审计）
    8. 获取 service action
    9. 直接调用 service 层入库（dry-run 时跳过）
    10. 生成 receipt（回执）

用法示例：
    python -m ingest_center.run_one --manifest manifests/xxx.json
    python -m ingest_center.run_one --manifest manifests/xxx.json --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from . import config
from . import dispatcher
from . import file_checks
from . import http_client
from . import manifest_model
from . import payload_builder
from . import staging_loader
from . import validators


# config.PROJECT_ROOT 指向 backend/，真正的项目根目录是其上级
_PROJECT_ROOT = os.path.dirname(config.PROJECT_ROOT)


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

    优先查找常见字段名：count / total / written_count / created_count。
    取不到则返回 None。
    """
    if response_data is None:
        return None

    if isinstance(response_data, list):
        return len(response_data)

    if isinstance(response_data, dict):
        for key in ("total", "count", "written_count", "created_count"):
            val = response_data.get(key)
            if isinstance(val, int):
                return val

        # 尝试嵌套查找（如 ingest_financial_package 返回的 {"stock_daily": {"total": 5}}）
        for value in response_data.values():
            if isinstance(value, dict):
                for sub_key in ("total", "count", "written_count", "created_count"):
                    sub_val = value.get(sub_key)
                    if isinstance(sub_val, int):
                        return sub_val
            elif isinstance(value, list):
                return len(value)

    return None


def _write_receipt(receipt: Dict[str, Any], job_id: str) -> str:
    """
    将 receipt 写入 receipts 目录。

    Args:
        receipt: receipt 字典。
        job_id: 任务 ID，用于生成文件名。

    Returns:
        写入的 receipt 文件路径。
    """
    os.makedirs(config.RECEIPT_DIR, exist_ok=True)
    receipt_path = os.path.join(config.RECEIPT_DIR, f"{job_id}.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    return receipt_path


def _build_receipt(
    *,
    manifest_obj: manifest_model.Manifest,
    manifest_path: str,
    staging_path: str,
    endpoint: Optional[str],
    status: str,
    success: bool,
    error_message: Optional[str],
    error_code: Optional[str],
    trace_id: Optional[str],
    warnings: Optional[list],
    response_data: Optional[Any],
    http_status: Optional[int] = None,
    dry_run: bool = False,
    written_count: Optional[int] = None,
) -> Dict[str, Any]:
    """构造 receipt 字典。"""
    return {
        "job_id": manifest_obj.job_id,
        "data_category": manifest_obj.data_category,
        "manifest_path": manifest_path,
        "staging_path": staging_path,
        "endpoint": endpoint,
        "status": status,
        "success": success,
        "written_count": written_count if written_count is not None else _extract_written_count(response_data),
        "error_code": error_code,
        "error_message": error_message,
        "trace_id": trace_id,
        "warnings": warnings,
        "http_status": http_status,
        "dry_run": dry_run,
        "created_at": _now_iso(),
    }


def _validate_endpoint_string(endpoint: str) -> None:
    """
    校验 endpoint 字符串本身不能包含非法引号或首尾空白。

    Raises:
        ValueError: 校验不通过。
    """
    stripped = endpoint.strip()
    if stripped != endpoint:
        raise ValueError(
            f"endpoint contains leading/trailing whitespace: {endpoint!r}"
        )
    if stripped.startswith(("'", '"')) or stripped.endswith(("'", '"')):
        raise ValueError(
            f"endpoint contains illegal quotes: {endpoint!r}"
        )


def _validate_manifest_legality(manifest_obj: manifest_model.Manifest) -> None:
    """
    校验 manifest 的合法性。

    检查项：
        - spec_version 必须为 "1.0"
        - data_category 必须在 ALLOWED_CATEGORIES ∪ SKIP_INGEST_CATEGORIES 中
        - target.endpoint 必须与 dispatcher.CATEGORY_ENDPOINT_MAP 一致（patent 除外）
        - target.endpoint 本身不能包含首尾空白或引号

    Raises:
        ValueError: 校验不通过。
    """
    if manifest_obj.spec_version != "1.0":
        raise ValueError(
            f"unsupported spec_version: {manifest_obj.spec_version}, expected '1.0'"
        )

    valid_categories = config.ALLOWED_CATEGORIES | config.SKIP_INGEST_CATEGORIES
    if manifest_obj.data_category not in valid_categories:
        raise ValueError(
            f"invalid data_category: {manifest_obj.data_category}, "
            f"must be one of {sorted(valid_categories)}"
        )

    _validate_endpoint_string(manifest_obj.target.endpoint)

    if manifest_obj.data_category not in config.SKIP_INGEST_CATEGORIES:
        mapped_endpoint = dispatcher.CATEGORY_ENDPOINT_MAP.get(manifest_obj.data_category)
        if mapped_endpoint and manifest_obj.target.endpoint != mapped_endpoint:
            raise ValueError(
                f"endpoint mismatch: manifest says {manifest_obj.target.endpoint}, "
                f"dispatcher expects {mapped_endpoint}"
            )


def run(manifest_path: str, dry_run: bool = False) -> None:
    """
    执行单任务入库主流程。

    Args:
        manifest_path: manifest JSON 文件路径。
        dry_run: 为 True 时不调用 service，仅执行本地校验与 payload 构造。
    """
    # 1. 解析 manifest
    manifest_obj = manifest_model.parse_manifest(manifest_path)
    data_category = manifest_obj.data_category
    staging_path = _resolve_path(manifest_obj.files.staging_path)
    expected_endpoint = manifest_obj.target.endpoint

    # 2. manifest 合法性校验
    try:
        _validate_manifest_legality(manifest_obj)
    except ValueError as exc:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=str(exc),
            error_code="VALIDATION_ERROR",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] manifest illegal: {exc}")
        sys.exit(1)

    # 3. 如果 data_category 在 SKIP_INGEST_CATEGORIES，直接写 skipped receipt
    if data_category in config.SKIP_INGEST_CATEGORIES:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=None,
            status="skipped",
            success=True,
            error_message=None,
            error_code=None,
            trace_id=None,
            warnings=None,
            response_data=None,
            written_count=0,
            dry_run=dry_run,
        )
        receipt_path = _write_receipt(receipt, manifest_obj.job_id)
        print(f"[SKIP] {data_category} skipped. receipt written to {receipt_path}")
        return

    # 4. 校验 staging 文件存在
    try:
        file_checks.ensure_file_exists(staging_path)
    except FileNotFoundError as exc:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=str(exc),
            error_code="FILE_NOT_FOUND",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] {exc}")
        sys.exit(1)

    # 5. 校验 staging sha256
    try:
        file_checks.verify_sha256(staging_path, manifest_obj.checksum.staging_sha256)
    except ValueError as exc:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=str(exc),
            error_code="CHECKSUM_MISMATCH",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] {exc}")
        sys.exit(1)

    # 6. 加载 staging
    staging = staging_loader.load_staging(staging_path)

    # 7. 提取 records
    records = staging_loader.extract_records(data_category, staging)

    # 8. 校验 records
    validation_errors = validators.validate_records(data_category, records)
    if validation_errors:
        error_text = "; ".join(validation_errors)
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=error_text,
            error_code="VALIDATION_ERROR",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] validation failed: {error_text}")
        sys.exit(1)

    # 9. 构造 payload
    payload = payload_builder.build_payload(data_category, staging)

    # 10. 校验 endpoint 一致性（仅审计）
    mapped_endpoint = dispatcher.CATEGORY_ENDPOINT_MAP.get(data_category)
    if mapped_endpoint is None:
        err = f"no endpoint mapping for data_category: {data_category}"
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=err,
            error_code="CONFIG_ERROR",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] {err}")
        sys.exit(1)

    if expected_endpoint != mapped_endpoint:
        err = (
            f"endpoint mismatch: manifest says {expected_endpoint}, "
            f"dispatcher expects {mapped_endpoint}"
        )
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=err,
            error_code="CONFIG_ERROR",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] {err}")
        sys.exit(1)

    # 11. 获取 service action
    try:
        action = dispatcher.get_service_action(data_category)
    except KeyError as exc:
        err = f"no service action for data_category: {data_category}"
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=err,
            error_code="CONFIG_ERROR",
            trace_id=None,
            warnings=None,
            response_data=None,
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] {err}")
        sys.exit(1)

    # 12. dry-run 分支：不调用 service，直接写 validated receipt
    if dry_run:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="validated",
            success=True,
            error_message=None,
            error_code=None,
            trace_id=None,
            warnings=None,
            response_data=None,
            http_status=None,
            dry_run=True,
        )
        receipt_path = _write_receipt(receipt, manifest_obj.job_id)
        print(f"[VALIDATED] {data_category} dry-run passed. receipt written to {receipt_path}")
        return

    # 13. 直接调用 service 层
    result = http_client.call_service(action, payload)

    if not result["ok"]:
        receipt = _build_receipt(
            manifest_obj=manifest_obj,
            manifest_path=manifest_path,
            staging_path=staging_path,
            endpoint=expected_endpoint,
            status="failed",
            success=False,
            error_message=result["error_message"],
            error_code=result["error_code"],
            trace_id=result["trace_id"],
            warnings=result.get("warnings"),
            response_data=result.get("response_data"),
        )
        _write_receipt(receipt, manifest_obj.job_id)
        print(f"[FAIL] service error: {result['error_message']}")
        # 透传 warnings（通常包含 traceback）到控制台
        for w in result.get("warnings") or []:
            print(f"  warning: {w}")
        sys.exit(1)

    # 14. 成功，写 done receipt
    receipt = _build_receipt(
        manifest_obj=manifest_obj,
        manifest_path=manifest_path,
        staging_path=staging_path,
        endpoint=expected_endpoint,
        status="done",
        success=True,
        error_message=None,
        error_code=None,
        trace_id=result.get("trace_id"),
        warnings=result.get("warnings"),
        response_data=result.get("response_data"),
    )
    receipt_path = _write_receipt(receipt, manifest_obj.job_id)
    print(f"[DONE] {data_category} ingested. receipt written to {receipt_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a single manifest into the backend.")
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the manifest JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all local validations and payload building without calling service.",
    )
    args = parser.parse_args()
    run(args.manifest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
