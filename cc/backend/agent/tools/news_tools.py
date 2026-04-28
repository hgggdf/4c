"""新闻与舆情查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import (
    ImpactSummaryRequest,
    IndustryDaysRequest,
    NewsRawRequest,
    StockCodeDaysRequest,
)


def get_news_raw(days: int = 30, news_type: str | None = None) -> list[dict[str, Any]]:
    """
    获取原始新闻数据

    Args:
        days: 查询最近N天的新闻，默认30天
        news_type: 新闻类型过滤，可选

    Returns:
        原始新闻列表，每条包含：
        - id: 新闻ID
        - news_uid: 新闻唯一标识
        - title: 新闻标题
        - publish_time: 发布时间
        - source_name: 来源名称
        - source_url: 来源URL
        - author_name: 作者
        - content: 新闻内容
        - news_type: 新闻类型
        - language: 语言
    """
    container = ServiceContainer.build_default()
    req = NewsRawRequest(days=days, news_type=news_type)
    result = container.news.get_news_raw(req)
    if not result.success:
        raise ValueError(f"获取原始新闻失败: {result.message}")
    return result.data


def get_news_by_company(stock_code: str, days: int = 90) -> list[dict[str, Any]]:
    """
    获取公司相关新闻及影响分析

    Args:
        stock_code: 股票代码
        days: 查询最近N天的新闻，默认90天

    Returns:
        公司新闻列表，每条包含新闻基本信息及：
        - impact_direction: 影响方向（positive/negative/neutral）
        - impact_strength: 影响强度（0-1）
        - reason_text: 影响原因说明
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.news.get_news_by_company(req)
    if not result.success:
        raise ValueError(f"获取公司新闻失败: {result.message}")
    return result.data


def get_news_by_industry(industry_code: str, days: int = 30) -> list[dict[str, Any]]:
    """
    获取行业相关新闻及影响分析

    Args:
        industry_code: 行业代码
        days: 查询最近N天的新闻，默认30天

    Returns:
        行业新闻列表，每条包含新闻基本信息及：
        - impact_direction: 影响方向（positive/negative/neutral）
        - impact_strength: 影响强度（0-1）
        - reason_text: 影响原因说明
    """
    container = ServiceContainer.build_default()
    req = IndustryDaysRequest(industry_code=industry_code, days=days)
    result = container.news.get_news_by_industry(req)
    if not result.success:
        raise ValueError(f"获取行业新闻失败: {result.message}")
    return result.data


def get_company_news_impact(stock_code: str, days: int = 90) -> dict[str, Any]:
    """
    获取公司新闻影响汇总分析

    Args:
        stock_code: 股票代码
        days: 查询最近N天，默认90天

    Returns:
        新闻影响汇总字典，包含：
        - stock_code: 股票代码
        - days: 查询天数
        - items: 新闻列表（含影响方向和强度）
        - impact_events: 影响事件列表
        - direction_counts: 按影响方向统计的数量
        - avg_impact_strength: 平均影响强度
        - evidence: 向量检索证据（如有）
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.news.get_company_news_impact(req)
    if not result.success:
        raise ValueError(f"获取公司新闻影响分析失败: {result.message}")
    return result.data


def get_industry_news_impact(industry_code: str, days: int = 30) -> dict[str, Any]:
    """
    获取行业新闻影响汇总分析

    Args:
        industry_code: 行业代码
        days: 查询最近N天，默认30天

    Returns:
        行业新闻影响汇总字典，包含：
        - industry_code: 行业代码
        - days: 查询天数
        - items: 新闻列表（含影响方向和强度）
        - impact_events: 影响事件列表
        - direction_counts: 按影响方向统计的数量
        - avg_impact_strength: 平均影响强度
        - evidence: 向量检索证据（如有）
    """
    container = ServiceContainer.build_default()
    req = IndustryDaysRequest(industry_code=industry_code, days=days)
    result = container.news.get_industry_news_impact(req)
    if not result.success:
        raise ValueError(f"获取行业新闻影响分析失败: {result.message}")
    return result.data


__all__ = [
    "get_news_raw",
    "get_news_by_company",
    "get_news_by_industry",
    "get_company_news_impact",
    "get_industry_news_impact",
]
