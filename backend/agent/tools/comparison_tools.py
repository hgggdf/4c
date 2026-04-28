"""多公司对比分析工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import FinancialMetricsRequest, StockCodeLimitRequest


def compare_financial_metrics(
    stock_codes: list[str], metric_names: list[str], limit: int = 4
) -> dict[str, Any]:
    """
    对比多家公司的财务指标

    Args:
        stock_codes: 股票代码列表，如 ["600276", "600196"]
        metric_names: 指标名称列表，如 ["gross_margin", "net_margin", "roe"]
        limit: 每个指标返回最近N期数据，默认4期

    Returns:
        对比结果字典：
        {
            "stock_codes": ["600276", "600196"],
            "metric_names": ["gross_margin", "net_margin"],
            "companies": {
                "600276": {"stock_name": "恒瑞医药", ...},
                "600196": {"stock_name": "复星医药", ...}
            },
            "comparison": {
                "gross_margin": {
                    "600276": [{"report_date": "2025-12-31", "value": 86.21}, ...],
                    "600196": [{"report_date": "2025-12-31", "value": 45.32}, ...]
                },
                "net_margin": {...}
            }
        }
    """
    container = ServiceContainer.build_default()

    # 验证股票代码
    if not stock_codes or len(stock_codes) < 2:
        raise ValueError("至少需要2家公司进行对比")
    if len(stock_codes) > 5:
        raise ValueError("最多支持5家公司对比")

    # 获取公司基本信息
    companies = {}
    for code in stock_codes:
        result = container.company.get_company_basic_info(code)
        if not result.success:
            raise ValueError(f"获取公司 {code} 信息失败: {result.message}")
        companies[code] = result.data

    # 并行查询各公司的财务指标
    comparison = {}
    for metric in metric_names:
        comparison[metric] = {}
        for code in stock_codes:
            req = FinancialMetricsRequest(
                stock_code=code, metric_names=[metric], limit=limit
            )
            result = container.financial.get_financial_metrics(req)
            if not result.success:
                comparison[metric][code] = []
                continue

            # 提取指标值
            values = []
            for item in result.data:
                values.append({
                    "report_date": item.get("report_date"),
                    "fiscal_year": item.get("fiscal_year"),
                    "value": item.get("metric_value"),
                    "unit": item.get("metric_unit"),
                })
            comparison[metric][code] = values

    return {
        "stock_codes": stock_codes,
        "metric_names": metric_names,
        "companies": companies,
        "comparison": comparison,
    }


def compare_revenue_growth(stock_codes: list[str], limit: int = 4) -> dict[str, Any]:
    """
    对比多家公司的营收增长率

    Args:
        stock_codes: 股票代码列表
        limit: 返回最近N期数据，默认4期

    Returns:
        对比结果字典，包含各公司营收和同比增长率
    """
    container = ServiceContainer.build_default()

    if not stock_codes or len(stock_codes) < 2:
        raise ValueError("至少需要2家公司进行对比")
    if len(stock_codes) > 5:
        raise ValueError("最多支持5家公司对比")

    # 获取公司基本信息
    companies = {}
    for code in stock_codes:
        result = container.company.get_company_basic_info(code)
        if not result.success:
            raise ValueError(f"获取公司 {code} 信息失败: {result.message}")
        companies[code] = result.data

    # 查询各公司利润表
    revenue_data = {}
    for code in stock_codes:
        req = StockCodeLimitRequest(stock_code=code, limit=limit)
        result = container.financial.get_income_statements(req)
        if not result.success:
            revenue_data[code] = []
            continue

        # 提取营收数据
        revenues = []
        for item in result.data:
            revenues.append({
                "report_date": item.get("report_date"),
                "fiscal_year": item.get("fiscal_year"),
                "report_type": item.get("report_type"),
                "revenue": item.get("revenue"),
            })
        revenue_data[code] = revenues

    # 计算同比增长率
    growth_data = {}
    for code, revenues in revenue_data.items():
        growth_data[code] = []
        for i, current in enumerate(revenues):
            if i < len(revenues) - 1:
                prev = revenues[i + 1]
                if prev.get("revenue") and current.get("revenue"):
                    growth_rate = (
                        (current["revenue"] - prev["revenue"]) / prev["revenue"] * 100
                    )
                    growth_data[code].append({
                        "report_date": current.get("report_date"),
                        "fiscal_year": current.get("fiscal_year"),
                        "revenue": current.get("revenue"),
                        "growth_rate": round(growth_rate, 2),
                    })
                else:
                    growth_data[code].append({
                        "report_date": current.get("report_date"),
                        "fiscal_year": current.get("fiscal_year"),
                        "revenue": current.get("revenue"),
                        "growth_rate": None,
                    })
            else:
                growth_data[code].append({
                    "report_date": current.get("report_date"),
                    "fiscal_year": current.get("fiscal_year"),
                    "revenue": current.get("revenue"),
                    "growth_rate": None,
                })

    return {
        "stock_codes": stock_codes,
        "companies": companies,
        "revenue_growth": growth_data,
    }


__all__ = [
    "compare_financial_metrics",
    "compare_revenue_growth",
]
