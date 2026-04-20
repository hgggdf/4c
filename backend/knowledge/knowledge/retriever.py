from __future__ import annotations

import re
from typing import Any

from knowledge.store import get_store, get_vector_store

STRUCTURED_KEYWORDS = [
    "毛利率",
    "净利润",
    "营业收入",
    "营业总收入",
    "ROE",
    "净资产收益率",
    "资产负债率",
    "每股收益",
    "研发投入",
    "研发费用",
    "净利率",
    "流动比率",
    "速动比率",
    "存货周转",
    "应收账款",
    "多少",
    "是多少",
    "几亿",
    "增长了",
    "下降了",
    "同比",
    "CPI",
    "GDP",
    "宏观",
]

UNSTRUCTURED_KEYWORDS = [
    "分析",
    "研报",
    "前景",
    "风险",
    "机会",
    "投资价值",
    "管线",
    "集采",
    "医保",
    "政策",
    "竞争",
    "赛道",
    "行业",
    "为什么",
    "原因",
    "影响",
    "建议",
    "看法",
    "怎么样",
    "证据",
    "公告",
    "附注",
    "新闻",
    "舆情",
]

FORCE_STRUCTURED = [
    "近三年",
    "近几年",
    "历年",
    "趋势",
    "变化",
    "增长率",
    "多少",
    "是多少",
    "几亿",
    "同比",
]


def route_query(query: str) -> str:
    has_force = any(kw in query for kw in FORCE_STRUCTURED)
    has_unstructured = any(kw in query for kw in UNSTRUCTURED_KEYWORDS)
    if has_force:
        return "hybrid" if has_unstructured else "structured"

    s_score = sum(1 for kw in STRUCTURED_KEYWORDS if kw in query)
    u_score = sum(1 for kw in UNSTRUCTURED_KEYWORDS if kw in query)

    if s_score > 0 and u_score == 0:
        return "structured"
    if u_score > 0 and s_score == 0:
        return "unstructured"
    if s_score > 0 and u_score > 0:
        return "hybrid"
    return "unstructured"


def extract_year(text: str) -> int | None:
    m = re.search(r"(202[0-9]|201[0-9])", text)
    return int(m.group(1)) if m else None


def search_unstructured(
    query: str,
    top_k: int = 3,
    stock_code: str | None = None,
    industry_code: str | None = None,
    doc_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    轻量非结构化检索入口。
    不再做公司名硬编码解析。
    公司解析应由 CompanyService 完成。
    """
    query = (query or "").strip()
    if not query:
        return []

    filters: dict[str, Any] = {}
    if stock_code:
        filters["stock_code"] = stock_code
    if industry_code:
        filters["industry_code"] = industry_code

    try:
        store = get_vector_store()
        if store.count() == 0:
            hits = get_store().search(query, top_k=top_k)
        else:
            hits = store.search(
                query=query,
                top_k=top_k,
                doc_types=doc_types,
                filters=filters or None,
            )
        return hits
    except Exception:
        return []


def hybrid_search(
    query: str,
    top_k: int = 3,
    stock_code: str | None = None,
    industry_code: str | None = None,
) -> dict[str, Any]:
    """
    这里只做轻量 hybrid 封装。
    结构化部分由上层 service / repositories 负责。
    """
    route = route_query(query)
    return {
        "route": route,
        "stock_code": stock_code,
        "industry_code": industry_code,
        "year": extract_year(query),
        "unstructured_hits": search_unstructured(
            query=query,
            stock_code=stock_code,
            industry_code=industry_code,
            top_k=top_k,
        ),
    }