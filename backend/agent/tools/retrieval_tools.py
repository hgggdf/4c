"""向量检索工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import SearchRequest


def search_documents(
    query: str,
    stock_code: str | None = None,
    industry_code: str | None = None,
    doc_types: list[str] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    全库语义检索（公告、财务附注、新闻、研报等）

    Args:
        query: 检索查询文本
        stock_code: 限定股票代码（可选）
        industry_code: 限定行业代码（可选）
        doc_types: 文档类型过滤列表，可选值：
            ["announcement", "financial_note", "news", "report", "policy", "company_profile"]
        top_k: 返回最相关的N条结果，默认5

    Returns:
        检索结果列表，每条包含：
        - doc_type: 文档类型
        - source_id: 来源记录ID
        - chunk_id: 分块ID
        - score: 相似度分数
        - content: 匹配内容片段
        - 以及来源记录的原始字段（标题、日期、URL等）
    """
    container = ServiceContainer.build_default()
    req = SearchRequest(
        query=query,
        stock_code=stock_code,
        industry_code=industry_code,
        doc_types=doc_types,
        top_k=top_k,
    )
    result = container.retrieval.search_text_evidence(req)
    if not result.success:
        raise ValueError(f"文档检索失败: {result.message}")
    data = result.data or {}
    return data.get("items", [])


def search_company_evidence(
    query: str,
    stock_code: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    检索公司相关证据（公告、财务附注、公司资料）

    Args:
        query: 检索查询文本，如 "研发管线进展"、"集采影响"
        stock_code: 股票代码
        top_k: 返回最相关的N条结果，默认5

    Returns:
        检索结果列表，每条包含：
        - doc_type: 文档类型
        - source_id: 来源记录ID
        - score: 相似度分数
        - content: 匹配内容片段
        - 以及来源记录的原始字段
    """
    container = ServiceContainer.build_default()
    req = SearchRequest(
        query=query,
        stock_code=stock_code,
        top_k=top_k,
    )
    result = container.retrieval.search_text_evidence(req)
    if not result.success:
        raise ValueError(f"公司证据检索失败: {result.message}")
    data = result.data or {}
    return data.get("items", [])


def search_news_evidence(
    query: str,
    stock_code: str | None = None,
    industry_code: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    检索新闻证据（语义相关的新闻片段）

    Args:
        query: 检索查询文本
        stock_code: 限定股票代码（可选）
        industry_code: 限定行业代码（可选）
        top_k: 返回最相关的N条结果，默认5

    Returns:
        新闻证据列表，每条包含：
        - doc_type: "news"
        - source_id: 新闻ID
        - score: 相似度分数
        - summary: 新闻摘要（标题+内容前100字）
        - title: 新闻标题
        - publish_time: 发布时间
        - source_name: 来源名称
        - source_url: 来源URL
    """
    container = ServiceContainer.build_default()
    req = SearchRequest(
        query=query,
        stock_code=stock_code,
        industry_code=industry_code,
        top_k=top_k,
    )
    result = container.retrieval.search_news_evidence(req)
    if not result.success:
        raise ValueError(f"新闻证据检索失败: {result.message}")
    return result.data


__all__ = [
    "search_documents",
    "search_company_evidence",
    "search_news_evidence",
]
