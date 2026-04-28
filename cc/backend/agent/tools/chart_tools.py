"""图表构建工具 - 为医药分析生成前端可直接消费的 ECharts 配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChartConfig:
    chart_type: str          # bar / line / radar / pie
    title: str
    x_axis: list[str] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class PharmaChartBuilder:
    """医药分析图表构建器，输出标准 ECharts option 结构。"""

    def build_score_radar(
        self,
        dimensions: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """10维度评分雷达图。

        dimensions: [{"name": str, "score": float, "weight": float}, ...]
        """
        if not dimensions:
            return ChartConfig(chart_type="radar", title=f"{stock_name} 医药能力雷达图")

        indicators = [
            {"name": d["name"], "max": 100}
            for d in dimensions
        ]
        values = [round(d.get("score", 0), 1) for d in dimensions]

        return ChartConfig(
            chart_type="radar",
            title=f"{stock_name} 医药能力雷达图",
            series=[{
                "name": stock_name,
                "type": "radar",
                "data": [{"value": values, "name": stock_name}],
            }],
            extra={
                "radar": {"indicator": indicators},
                "legend": {"data": [stock_name]},
            },
        )

    def build_financial_trend(
        self,
        metric: str,
        points: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """财务指标趋势折线图。

        points: [{"year": int, "value": float, "unit": str}, ...]
        """
        x = [str(p.get("year") or p.get("period") or "") for p in points]
        y = [round(float(p["value"]), 4) if p.get("value") is not None else None for p in points]
        unit = points[0].get("unit", "") if points else ""

        return ChartConfig(
            chart_type="line",
            title=f"{stock_name} {metric} 趋势",
            x_axis=x,
            series=[{
                "name": metric,
                "type": "line",
                "data": y,
                "smooth": True,
                "markPoint": {
                    "data": [
                        {"type": "max", "name": "最大值"},
                        {"type": "min", "name": "最小值"},
                    ]
                },
            }],
            extra={
                "yAxis": {"name": unit},
                "tooltip": {"trigger": "axis"},
            },
        )

    def build_pipeline_bar(
        self,
        pipeline_data: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """管线阶段分布柱状图。

        pipeline_data: [{"stage": str, "count": int, "innovative": int}, ...]
        """
        if not pipeline_data:
            return ChartConfig(
                chart_type="bar",
                title=f"{stock_name} 管线阶段分布",
            )

        stages = [d.get("stage", "") for d in pipeline_data]
        total_counts = [d.get("count", 0) for d in pipeline_data]
        innovative_counts = [d.get("innovative", 0) for d in pipeline_data]

        return ChartConfig(
            chart_type="bar",
            title=f"{stock_name} 管线阶段分布",
            x_axis=stages,
            series=[
                {
                    "name": "总数",
                    "type": "bar",
                    "data": total_counts,
                    "stack": "total",
                },
                {
                    "name": "创新药",
                    "type": "bar",
                    "data": innovative_counts,
                    "stack": "total",
                },
            ],
            extra={
                "legend": {"data": ["总数", "创新药"]},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            },
        )

    def build_score_bar(
        self,
        dimensions: list[dict[str, Any]],
        stock_name: str,
    ) -> ChartConfig:
        """各维度得分水平条形图（雷达图的备选展示形式）。"""
        if not dimensions:
            return ChartConfig(chart_type="bar", title=f"{stock_name} 各维度得分")

        sorted_dims = sorted(dimensions, key=lambda d: d.get("score", 0))
        names = [d["name"] for d in sorted_dims]
        scores = [round(d.get("score", 0), 1) for d in sorted_dims]
        colors = [
            "#ee6666" if s < 50 else "#fac858" if s < 70 else "#91cc75"
            for s in scores
        ]

        return ChartConfig(
            chart_type="bar",
            title=f"{stock_name} 各维度得分",
            x_axis=names,
            series=[{
                "name": "得分",
                "type": "bar",
                "data": [
                    {"value": s, "itemStyle": {"color": c}}
                    for s, c in zip(scores, colors)
                ],
                "label": {"show": True, "position": "right"},
            }],
            extra={
                "xAxis": {"max": 100},
                "yAxis": {"type": "category"},
                "tooltip": {"trigger": "axis"},
            },
        )

    def build_from_score_result(
        self,
        dimensions: list[dict[str, Any]],
        financial_trends: list[dict[str, Any]],
        pipeline_stages: list[dict[str, Any]],
        stock_name: str,
    ) -> list[ChartConfig]:
        """一次性生成全套图表：雷达图 + 财务趋势 + 管线分布。"""
        charts: list[ChartConfig] = []

        if dimensions:
            charts.append(self.build_score_radar(dimensions, stock_name))

        for trend in financial_trends:
            metric = trend.get("metric", "")
            points = trend.get("points", [])
            if metric and points:
                charts.append(self.build_financial_trend(metric, points, stock_name))

        if pipeline_stages:
            charts.append(self.build_pipeline_bar(pipeline_stages, stock_name))

        return charts


__all__ = ["PharmaChartBuilder", "ChartConfig"]
