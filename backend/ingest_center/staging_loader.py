"""
ingest_center / staging_loader.py
================================

Staging 数据读取与记录提取模块。

职责：
    负责将 staging JSON 文件加载为内存中的字典，
    并根据 data_category 提取出待校验的记录列表。
"""

import json
from typing import Any, Dict, List


def load_staging(path: str) -> Dict[str, Any]:
    """
    读取单个 staging JSON 文件。

    Args:
        path: staging 文件路径。

    Returns:
        staging 字典。
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_records(data_category: str, staging: Dict[str, Any]) -> List[Any]:
    """
    根据 data_category 从 staging 字典中提取记录列表。

    Args:
        data_category: 数据类别。
        staging: 已加载的 staging 字典。

    Returns:
        记录列表。

    Raises:
        KeyError: staging 中缺少对应分类所需的键。
    """
    payload = staging.get("payload", {})

    if data_category == "company":
        return [payload]

    if data_category == "stock_daily":
        return payload["stock_daily"]

    if data_category == "announcement_raw":
        return payload["raw_announcements"]

    if data_category == "research_report":
        return payload["news_raw"]

    if data_category == "financial_package":
        payload = staging.get("payload", {})
        records = []
        for key in (
            "income_statements",
            "balance_sheets",
            "cashflow_statements",
            "financial_metrics",
            "financial_notes",
            "business_segments",
        ):
            records.extend(payload.get(key) or [])
        return records

    if data_category in ("macro", "patent"):
        return staging["records"]

    raise ValueError(f"unknown data_category for record extraction: {data_category}")
