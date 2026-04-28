"""财务数据查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import (
    FinancialMetricsRequest,
    FinancialSummaryRequest,
    StockCodeLimitRequest,
)


def get_income_statements(stock_code: str, limit: int = 4) -> list[dict[str, Any]]:
    """
    获取利润表数据

    Args:
        stock_code: 股票代码
        limit: 返回最近N期数据，默认4期

    Returns:
        利润表列表，每期包含：
        - report_date: 报告期
        - fiscal_year: 会计年度
        - report_type: 报告类型（年报/半年报/季报）
        - revenue: 营业收入
        - operating_cost: 营业成本
        - gross_profit: 毛利润
        - selling_expense: 销售费用
        - admin_expense: 管理费用
        - rd_expense: 研发费用
        - operating_profit: 营业利润
        - net_profit: 净利润
        - net_profit_deducted: 扣非净利润
        - eps: 每股收益
    """
    container = ServiceContainer.build_default()
    req = StockCodeLimitRequest(stock_code=stock_code, limit=limit)
    result = container.financial.get_income_statements(req)
    if not result.success:
        raise ValueError(f"获取利润表失败: {result.message}")
    return result.data


def get_balance_sheets(stock_code: str, limit: int = 4) -> list[dict[str, Any]]:
    """
    获取资产负债表数据

    Args:
        stock_code: 股票代码
        limit: 返回最近N期数据，默认4期

    Returns:
        资产负债表列表，每期包含：
        - report_date: 报告期
        - fiscal_year: 会计年度
        - report_type: 报告类型
        - total_assets: 总资产
        - total_liabilities: 总负债
        - accounts_receivable: 应收账款
        - inventory: 存货
        - cash: 货币资金
        - equity: 股东权益
        - goodwill: 商誉
    """
    container = ServiceContainer.build_default()
    req = StockCodeLimitRequest(stock_code=stock_code, limit=limit)
    result = container.financial.get_balance_sheets(req)
    if not result.success:
        raise ValueError(f"获取资产负债表失败: {result.message}")
    return result.data


def get_cashflow_statements(stock_code: str, limit: int = 4) -> list[dict[str, Any]]:
    """
    获取现金流量表数据

    Args:
        stock_code: 股票代码
        limit: 返回最近N期数据，默认4期

    Returns:
        现金流量表列表，每期包含：
        - report_date: 报告期
        - fiscal_year: 会计年度
        - report_type: 报告类型
        - operating_cashflow: 经营活动现金流
        - investing_cashflow: 投资活动现金流
        - financing_cashflow: 筹资活动现金流
        - free_cashflow: 自由现金流
    """
    container = ServiceContainer.build_default()
    req = StockCodeLimitRequest(stock_code=stock_code, limit=limit)
    result = container.financial.get_cashflow_statements(req)
    if not result.success:
        raise ValueError(f"获取现金流量表失败: {result.message}")
    return result.data


def get_financial_metrics(
    stock_code: str, metric_names: list[str], limit: int = 4
) -> list[dict[str, Any]]:
    """
    获取财务指标数据

    Args:
        stock_code: 股票代码
        metric_names: 指标名称列表，如 ["gross_margin", "net_margin", "roe", "rd_ratio"]
        limit: 每个指标返回最近N期数据，默认4期

    Returns:
        财务指标列表，每条包含：
        - report_date: 报告期
        - fiscal_year: 会计年度
        - metric_name: 指标名称
        - metric_value: 指标值
        - metric_unit: 单位
        - calc_method: 计算方法
    """
    container = ServiceContainer.build_default()
    req = FinancialMetricsRequest(
        stock_code=stock_code, metric_names=metric_names, limit=limit
    )
    result = container.financial.get_financial_metrics(req)
    if not result.success:
        raise ValueError(f"获取财务指标失败: {result.message}")
    return result.data


def get_business_segments(stock_code: str, limit: int = 4) -> list[dict[str, Any]]:
    """
    获取业务分部数据

    Args:
        stock_code: 股票代码
        limit: 返回最近N期数据，默认4期

    Returns:
        业务分部列表，每条包含：
        - report_date: 报告期
        - segment_name: 分部名称
        - segment_type: 分部类型（产品/地区）
        - revenue: 分部收入
        - revenue_ratio: 收入占比
        - gross_margin: 毛利率
    """
    container = ServiceContainer.build_default()
    req = StockCodeLimitRequest(stock_code=stock_code, limit=limit)
    result = container.financial.get_business_segments(req)
    if not result.success:
        raise ValueError(f"获取业务分部失败: {result.message}")
    return result.data


def get_financial_summary(stock_code: str, period_count: int = 4) -> dict[str, Any]:
    """
    获取财务数据汇总（包含利润表、资产负债表、现金流量表、关键指标）

    Args:
        stock_code: 股票代码
        period_count: 返回最近N期数据，默认4期

    Returns:
        财务汇总字典，包含：
        - stock_code: 股票代码
        - latest_income: 最新一期利润表
        - latest_balance: 最新一期资产负债表
        - latest_cashflow: 最新一期现金流量表
        - income_statements: 利润表列表
        - balance_sheets: 资产负债表列表
        - cashflow_statements: 现金流量表列表
        - key_metrics: 关键指标列表（毛利率、净利率、研发费用率、资产负债率、ROE）
    """
    container = ServiceContainer.build_default()
    req = FinancialSummaryRequest(stock_code=stock_code, period_count=period_count)
    result = container.financial.get_financial_summary(req)
    if not result.success:
        raise ValueError(f"获取财务汇总失败: {result.message}")
    return result.data


__all__ = [
    "get_income_statements",
    "get_balance_sheets",
    "get_cashflow_statements",
    "get_financial_metrics",
    "get_business_segments",
    "get_financial_summary",
]
