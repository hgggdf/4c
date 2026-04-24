"""
ingest_center / validators.py
============================

按 data_category 分开的 staging 校验器模块。

职责：
    在正式调用入库接口前，针对不同 data_category 的 staging 数据
    执行相应的字段与格式校验，确保入库数据质量。

当前支持：
    - validate_company_staging
    - validate_stock_daily_staging
    - validate_announcement_staging
    - validate_research_report_staging
    - validate_macro_staging
    - validate_patent_staging（仅校验文件存在与格式，不允许进入入库链）

统一入口：
    - validate_records(data_category, records)
"""

from typing import Any, Dict, List


def _is_empty(value: Any) -> bool:
    """判断值是否为空（None 或空字符串）。"""
    return value is None or (isinstance(value, str) and value.strip() == "")


def validate_company_staging(records: List[Any]) -> List[str]:
    """
    校验 company staging 数据。

    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []

    if len(records) != 1:
        errors.append(f"company records length must be 1, got {len(records)}")
        return errors

    payload = records[0]
    if not isinstance(payload, dict):
        errors.append("company record must be a dict")
        return errors

    if "company_master" not in payload:
        errors.append("missing company_master in payload")
        return errors

    master = payload["company_master"]
    if not isinstance(master, dict):
        errors.append("company_master must be a dict")
        return errors

    if _is_empty(master.get("stock_code")):
        errors.append("missing or empty company_master.stock_code")

    if _is_empty(master.get("stock_name")) and _is_empty(master.get("full_name")):
        errors.append("missing or empty company_master.stock_name or company_master.full_name")

    if _is_empty(master.get("exchange")):
        errors.append("missing or empty company_master.exchange")

    # 若存在 company_profile，至少校验其为 dict（不校验具体字段，避免阻断真实 OpenClaw 数据）
    if "company_profile" in payload and not isinstance(payload["company_profile"], dict):
        errors.append("company_profile must be a dict if present")

    return errors


def validate_stock_daily_staging(records: List[Any]) -> List[str]:
    """
    校验 stock_daily staging 数据。

    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []
    required = ["stock_code", "trade_date", "open_price", "close_price", "high_price", "low_price"]

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{idx}] is not a dict")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record[{idx}] missing field: {field}")
            elif _is_empty(record[field]):
                errors.append(f"record[{idx}] empty field: {field}")

    return errors


def validate_announcement_staging(records: List[Any]) -> List[str]:
    """
    校验 announcement_raw staging 数据。

    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []
    required = ["stock_code", "title", "publish_date", "content", "source_url"]

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{idx}] is not a dict")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record[{idx}] missing field: {field}")
            elif _is_empty(record[field]):
                errors.append(f"record[{idx}] empty field: {field}")

    return errors


def validate_research_report_staging(records: List[Any]) -> List[str]:
    """
    校验 research_report staging 数据。

    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []
    required = ["title", "publish_time", "content", "news_type", "source_url"]

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{idx}] is not a dict")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record[{idx}] missing field: {field}")
            elif _is_empty(record[field]):
                errors.append(f"record[{idx}] empty field: {field}")

    return errors


def validate_macro_staging(records: List[Any]) -> List[str]:
    """
    校验 macro staging 数据。

    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []
    required = ["indicator_name", "period", "value"]

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{idx}] is not a dict")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record[{idx}] missing field: {field}")
            elif _is_empty(record[field]):
                errors.append(f"record[{idx}] empty field: {field}")

    return errors


def validate_patent_staging(records: List[Any]) -> List[str]:
    """
    校验 patent staging 数据。

    仅校验基本格式，不报 endpoint 相关错误。
    返回错误信息列表；空列表表示通过。
    """
    errors: List[str] = []

    if not isinstance(records, list):
        errors.append("patent records must be a list")
        return errors

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{idx}] is not a dict")

    return errors


_VALIDATOR_MAP = {
    "company": validate_company_staging,
    "stock_daily": validate_stock_daily_staging,
    "announcement_raw": validate_announcement_staging,
    "research_report": validate_research_report_staging,
    "macro": validate_macro_staging,
    "patent": validate_patent_staging,
}


def validate_records(data_category: str, records: List[Any]) -> List[str]:
    """
    统一校验入口，根据 data_category 分发到对应校验器。

    Args:
        data_category: 数据类别。
        records: 记录列表。

    Returns:
        错误信息列表；空列表表示通过。

    Raises:
        ValueError: 未知的 data_category。
    """
    validator = _VALIDATOR_MAP.get(data_category)
    if validator is None:
        raise ValueError(f"no validator for data_category: {data_category}")
    return validator(records)
