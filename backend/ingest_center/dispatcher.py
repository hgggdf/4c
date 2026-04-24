"""
ingest_center / dispatcher.py
============================

数据类别到后端 service action 的映射模块。

职责：
    根据 data_category 将已校验的 staging 记录路由到对应的 service 方法。
    manifest.target.endpoint 仅用于审计校验，不再作为真实传输目标。

映射规则（service action）：
    - company          -> ingest_company_package
    - stock_daily      -> ingest_financial_package
    - announcement_raw -> ingest_announcement_package
    - research_report  -> ingest_news_package
    - macro            -> batch_upsert_macro_indicators
    - patent           -> skip（不允许入库）

历史映射（endpoint，仅用于 audit）：
    - company          -> /api/ingest/company-package
    - stock_daily      -> /api/ingest/financial-package
    - announcement_raw -> /api/ingest/announcement-package
    - research_report  -> /api/ingest/news-package
    - macro            -> /api/macro-write/macro-indicators
"""

from typing import Any, Dict, List

# data_category -> 后端入库 API endpoint 路径映射（仅用于 audit 校验）
CATEGORY_ENDPOINT_MAP: Dict[str, str] = {
    "company": "/api/ingest/company-package",
    "stock_daily": "/api/ingest/financial-package",
    "announcement_raw": "/api/ingest/announcement-package",
    "research_report": "/api/ingest/news-package",
    "macro": "/api/macro-write/macro-indicators",
    "financial_package": "/api/ingest/financial-package",
}

# data_category -> service action 名称映射（真实调用目标）
CATEGORY_SERVICE_ACTION_MAP: Dict[str, str] = {
    "company": "ingest_company_package",
    "stock_daily": "ingest_financial_package",
    "announcement_raw": "ingest_announcement_package",
    "research_report": "ingest_news_package",
    "macro": "batch_upsert_macro_indicators",
    "financial_package": "ingest_financial_package",
}

# 模块加载时断言：endpoint 值不能包含首尾空白或引号
for _cat, _ep in CATEGORY_ENDPOINT_MAP.items():
    if _ep != _ep.strip():
        raise ValueError(f"dispatcher endpoint for {_cat!r} contains whitespace: {_ep!r}")
    if _ep.startswith(("'", '"')) or _ep.endswith(("'", '"')):
        raise ValueError(f"dispatcher endpoint for {_cat!r} contains illegal quotes: {_ep!r}")


def get_endpoint(data_category: str) -> str:
    """
    根据 data_category 获取对应的后端 endpoint（仅用于 audit 校验）。

    Args:
        data_category: 数据类别。

    Returns:
        endpoint 路径。

    Raises:
        KeyError: 如果 data_category 不在映射表中（如 patent）。
    """
    return CATEGORY_ENDPOINT_MAP[data_category]


def get_service_action(data_category: str) -> str:
    """
    根据 data_category 获取对应的 service action 名称（真实调用目标）。

    Args:
        data_category: 数据类别。

    Returns:
        service action 名称。

    Raises:
        KeyError: 如果 data_category 不在映射表中（如 patent）。
    """
    return CATEGORY_SERVICE_ACTION_MAP[data_category]


def dispatch(data_category: str, records: List[Any]) -> Dict[str, Any]:
    """
    根据 data_category 将 records 分发到对应 service 方法入库。

    Args:
        data_category: 数据类别。
        records: 已校验的 staging 记录列表。

    Returns:
        后端接口的响应摘要。
    """
    raise NotImplementedError
