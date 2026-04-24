"""图表构建工具骨架 - 为医药分析生成图表配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChartConfig:
    chart_type: str  # bar / line / radar / pie
    title: str
    x_axis: list[str] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class PharmaChartBuilder:
    """医药分析图表构建器。"""

    def build_score_radar(
        self,
        dimensions: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """构建10维度评分雷达图。"""
        # TODO: M3阶段实现
        return ChartConfig(
            chart_type="radar",
            title=f"{stock_name} 医药能力雷达图",
            extra={"dimensions": dimensions},
        )

    def build_financial_trend(
        self,
        metric: str,
        points: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """构建财务指标趋势折线图。"""
        # TODO: M3阶段实现
        return ChartConfig(
            chart_type="line",
            title=f"{stock_name} {metric} 趋势",
            x_axis=[str(p.get("year") or p.get("period") or "") for p in points],
            series=[{"name": metric, "data": [p.get("value") for p in points]}],
        )

    def build_pipeline_bar(
        self,
        pipeline_data: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """构建管线阶段分布柱状图。"""
        # TODO: M3阶段实现
        return ChartConfig(
            chart_type="bar",
            title=f"{stock_name} 管线阶段分布",
            extra={"pipeline": pipeline_data},
        )


__all__ = ["PharmaChartBuilder", "ChartConfig"]
