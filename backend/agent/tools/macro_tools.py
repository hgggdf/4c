"""宏观经济指标查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import (
    MacroIndicatorRequest,
    MacroListRequest,
    MacroSummaryRequest,
)


def get_macro_indicator(
    indicator_name: str, period: str | None = None
) -> dict[str, Any] | None:
    """
    获取单个宏观经济指标

    Args:
        indicator_name: 指标名称，如 "GDP增速"、"CPI"、"PMI"
        period: 期间（可选），如 "2024Q1"、"2024-03"

    Returns:
        指标数据字典，包含：
        - indicator_name: 指标名称
        - period: 期间
        - value: 指标值
        - unit: 单位
        - source_type: 数据来源类型
        - source_url: 数据来源URL
        - created_at: 创建时间
    """
    container = ServiceContainer.build_default()
    req = MacroIndicatorRequest(indicator_name=indicator_name, period=period)
    result = container.macro.get_macro_indicator(req)
    if not result.success:
        raise ValueError(f"获取宏观指标失败: {result.message}")
    return result.data


def list_macro_indicators(
    indicator_names: list[str], periods: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    批量获取多个宏观经济指标

    Args:
        indicator_names: 指标名称列表
        periods: 期间列表（可选），如果不指定则返回最新数据

    Returns:
        指标数据列表，每条包含：
        - indicator_name: 指标名称
        - period: 期间
        - value: 指标值
        - unit: 单位
        - source_type: 数据来源类型
        - source_url: 数据来源URL
    """
    container = ServiceContainer.build_default()
    req = MacroListRequest(indicator_names=indicator_names, periods=periods)
    result = container.macro.list_macro_indicators(req)
    if not result.success:
        raise ValueError(f"批量获取宏观指标失败: {result.message}")
    return result.data


def get_macro_summary(
    indicator_names: list[str], recent_n: int = 6
) -> dict[str, Any]:
    """
    获取宏观指标汇总（包含最近N期的时间序列）

    Args:
        indicator_names: 指标名称列表
        recent_n: 每个指标返回最近N期数据，默认6期

    Returns:
        宏观指标汇总字典，包含：
        - recent_n: 期数
        - series: 按指标名称分组的时间序列字典
            - {indicator_name: [最近N期数据列表]}
    """
    container = ServiceContainer.build_default()
    req = MacroSummaryRequest(indicator_names=indicator_names, recent_n=recent_n)
    result = container.macro.get_macro_summary(req)
    if not result.success:
        raise ValueError(f"获取宏观指标汇总失败: {result.message}")
    return result.data


__all__ = [
    "get_macro_indicator",
    "list_macro_indicators",
    "get_macro_summary",
]
