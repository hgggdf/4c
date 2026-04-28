"""公司信息查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import StockCodeRequest


def get_company_basic_info(stock_code: str) -> dict[str, Any]:
    """
    获取公司基本信息

    Args:
        stock_code: 股票代码，6位数字，如 "600519"

    Returns:
        包含公司基本信息的字典：
        - stock_code: 股票代码
        - stock_name: 股票简称
        - full_name: 公司全称
        - exchange: 交易所
        - industry_level1: 一级行业
        - industry_level2: 二级行业
        - listing_date: 上市日期
        - status: 状态
        - alias_json: 别名JSON
    """
    container = ServiceContainer.build_default()
    result = container.company.get_company_basic_info(stock_code)
    if not result.success:
        raise ValueError(f"获取公司基本信息失败: {result.message}")
    return result.data


def get_company_profile(stock_code: str) -> dict[str, Any] | None:
    """
    获取公司详细资料

    Args:
        stock_code: 股票代码

    Returns:
        包含公司详细资料的字典：
        - stock_code: 股票代码
        - business_summary: 业务概述
        - core_products_json: 核心产品JSON
        - main_segments_json: 主要业务板块JSON
        - market_position: 市场地位
        - management_summary: 管理层概述
    """
    container = ServiceContainer.build_default()
    result = container.company.get_company_profile(stock_code)
    if not result.success:
        raise ValueError(f"获取公司资料失败: {result.message}")
    return result.data


def get_company_overview(stock_code: str) -> dict[str, Any]:
    """
    获取公司完整概览（基本信息+资料+行业分类）

    Args:
        stock_code: 股票代码

    Returns:
        包含公司完整信息的字典：
        - 基本信息字段
        - profile: 公司资料对象
        - industries: 行业分类列表
    """
    container = ServiceContainer.build_default()
    result = container.company.get_company_overview(stock_code)
    if not result.success:
        raise ValueError(f"获取公司概览失败: {result.message}")
    return result.data


def resolve_company_from_text(text: str) -> list[dict[str, Any]]:
    """
    从文本中识别公司（支持公司名称、简称、别名）

    Args:
        text: 包含公司名称的文本，如 "恒瑞医药"、"贵州茅台"

    Returns:
        匹配的公司列表，每个公司包含：
        - stock_code: 股票代码
        - stock_name: 股票简称
        - full_name: 公司全称
        - exchange: 交易所
        - industry_level1: 一级行业
        - industry_level2: 二级行业
        - alias_json: 别名JSON
    """
    container = ServiceContainer.build_default()
    result = container.company.resolve_company(text)
    if not result.success:
        raise ValueError(f"识别公司失败: {result.message}")
    return result.data


__all__ = [
    "get_company_basic_info",
    "get_company_profile",
    "get_company_overview",
    "resolve_company_from_text",
]
