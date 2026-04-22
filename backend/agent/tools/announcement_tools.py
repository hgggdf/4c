"""公告事件查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import StockCodeDaysRequest


def get_raw_announcements(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取原始公告数据

    Args:
        stock_code: 股票代码
        days: 查询最近N天的公告，默认365天

    Returns:
        原始公告列表，每条包含：
        - id: 公告ID
        - stock_code: 股票代码
        - title: 公告标题
        - publish_date: 发布日期
        - announcement_type: 公告类型
        - exchange: 交易所
        - content: 公告内容
        - source_url: 来源URL
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_raw_announcements(req)
    if not result.success:
        raise ValueError(f"获取原始公告失败: {result.message}")
    return result.data


def get_structured_announcements(
    stock_code: str, days: int = 365, category: str | None = None
) -> list[dict[str, Any]]:
    """
    获取结构化公告数据

    Args:
        stock_code: 股票代码
        days: 查询最近N天的公告，默认365天
        category: 公告分类过滤，可选

    Returns:
        结构化公告列表，每条包含：
        - id: 结构化公告ID
        - announcement_id: 原始公告ID
        - stock_code: 股票代码
        - category: 分类（研发进展/财务业绩/监管处罚等）
        - summary_text: 摘要文本
        - key_fields_json: 关键字段JSON
        - signal_type: 信号类型（opportunity/risk/neutral）
        - risk_level: 风险等级
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days, category=category)
    result = container.announcement.get_structured_announcements(req)
    if not result.success:
        raise ValueError(f"获取结构化公告失败: {result.message}")
    return result.data


def get_drug_approvals(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取药品批准事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        药品批准事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - approval_type: 批准类型（上市批准/临床批准等）
        - approval_date: 批准日期
        - indication: 适应症
        - drug_stage: 药品阶段
        - is_innovative_drug: 是否创新药
        - review_status: 审评状态
        - market_scope: 市场范围
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_drug_approvals(req)
    if not result.success:
        raise ValueError(f"获取药品批准事件失败: {result.message}")
    return result.data


def get_clinical_trials(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取临床试验事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        临床试验事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - trial_phase: 试验阶段（I期/II期/III期）
        - event_type: 事件类型（启动/完成/中止等）
        - event_date: 事件日期
        - indication: 适应症
        - summary_text: 摘要文本
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_clinical_trials(req)
    if not result.success:
        raise ValueError(f"获取临床试验事件失败: {result.message}")
    return result.data


def get_procurement_events(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取集采中标事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        集采中标事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - procurement_round: 集采轮次
        - bid_result: 中标结果
        - price_change_ratio: 价格变化比例
        - event_date: 事件日期
        - impact_summary: 影响摘要
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_procurement_events(req)
    if not result.success:
        raise ValueError(f"获取集采中标事件失败: {result.message}")
    return result.data


def get_regulatory_risks(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取监管风险事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        监管风险事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - risk_type: 风险类型（处罚/警告/调查等）
        - event_date: 事件日期
        - risk_level: 风险等级
        - summary_text: 摘要文本
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_regulatory_risks(req)
    if not result.success:
        raise ValueError(f"获取监管风险事件失败: {result.message}")
    return result.data


def get_company_event_summary(stock_code: str, days: int = 365) -> dict[str, Any]:
    """
    获取公司事件汇总（包含所有类型的公告和事件）

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        事件汇总字典，包含：
        - stock_code: 股票代码
        - days: 查询天数
        - structured_announcements: 结构化公告列表
        - drug_approvals: 药品批准事件列表
        - clinical_trials: 临床试验事件列表
        - procurement_events: 集采中标事件列表
        - regulatory_risks: 监管风险事件列表
        - opportunity_items: 机会类公告列表
        - risk_items: 风险类公告列表
        - neutral_items: 中性公告列表
        - counts_by_category: 按分类统计的公告数量
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_company_event_summary(req)
    if not result.success:
        raise ValueError(f"获取公司事件汇总失败: {result.message}")
    return result.data


__all__ = [
    "get_raw_announcements",
    "get_structured_announcements",
    "get_drug_approvals",
    "get_clinical_trials",
    "get_procurement_events",
    "get_regulatory_risks",
    "get_company_event_summary",
]
