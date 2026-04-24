"""
ingest_center / payload_builder.py
=================================

Staging -> Request Payload 构造模块。

职责：
    将已校验的 staging 字典转换为后端入库接口所需的请求体结构。
    每个 data_category 对应独立的 payload 构造逻辑。
"""

from typing import Any, Dict


def build_payload(data_category: str, staging: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据 data_category 从 staging 构造后端入库请求体。

    Args:
        data_category: 数据类别。
        staging: 已加载的 staging 字典。

    Returns:
        后端接口所需的 payload 字典。

    Raises:
        ValueError: patent 不允许构造入库 payload。
        KeyError: staging 中缺少对应分类所需的键。
    """
    if data_category == "company":
        return staging["payload"]

    if data_category == "stock_daily":
        return staging["payload"]

    if data_category == "announcement_raw":
        payload = staging["payload"]
        return {
            "raw_announcements": payload.get("raw_announcements", []),
            "sync_vector_index": payload.get("sync_vector_index", False),
        }

    if data_category == "research_report":
        payload = staging["payload"]
        return {
            "news_raw": payload.get("news_raw", []),
            "sync_vector_index": payload.get("sync_vector_index", False),
        }

    if data_category == "macro":
        records = staging["records"]
        items = []
        for record in records:
            items.append({
                "indicator_name": record["indicator_name"],
                "period": record["period"],
                "value": record["value"],
                "unit": record.get("unit"),
                "source_type": record.get("source_type"),
                "source_url": record.get("source_url"),
            })
        return {
            "items": items,
            "sync_vector_index": False,
        }

    if data_category == "financial_package":
        payload = staging.get("payload") or {}
        return {
            "income_statements": payload.get("income_statements", []),
            "balance_sheets": payload.get("balance_sheets", []),
            "cashflow_statements": payload.get("cashflow_statements", []),
            "financial_metrics": payload.get("financial_metrics", []),
            "financial_notes": payload.get("financial_notes", []),
            "business_segments": payload.get("business_segments", []),
            "sync_vector_index": payload.get("sync_vector_index", False),
        }

    if data_category == "patent":
        raise ValueError("patent is not allowed to build ingest payload")

    raise ValueError(f"unknown data_category for payload building: {data_category}")
