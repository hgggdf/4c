"""医药分析引擎骨架 - M1阶段：可导入，返回 mock 结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.tools.pharma_decision_tools import PharmaDecisionTool, PharmaDecisionResult


@dataclass
class MedicalAnalysisResult:
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str
    dimensions: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    charts: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_missing: list[str] = field(default_factory=list)
    suggestion: str = ""


class MedicalAnalyzer:
    """医药分析引擎，供 glm_agent.py 调用。"""

    def __init__(self) -> None:
        self._decision_tool = PharmaDecisionTool()

    def analyze(
        self,
        stock_code: str,
        stock_name: str,
        year: int,
        query: str = "",
        financial_data: dict[str, Any] | None = None,
        pipeline_data: dict[str, Any] | None = None,
        raw_evidence: list[dict[str, Any]] | None = None,
    ) -> MedicalAnalysisResult:
        """执行医药综合分析，返回 MedicalAnalysisResult。"""
        decision: PharmaDecisionResult = self._decision_tool.analyze(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            query=query,
            financial_data=financial_data,
            pipeline_data=pipeline_data,
            raw_evidence=raw_evidence,
        )

        score = decision.score_result
        dimensions = (
            [
                {"name": d.name, "score": d.score, "weight": d.weight, "comment": d.comment}
                for d in score.dimensions
            ]
            if score
            else []
        )
        evidence_items = (
            [
                {"kind": e.kind, "title": e.title, "date": e.date, "source": e.source, "summary": e.summary}
                for e in decision.evidence.items
            ]
            if decision.evidence
            else []
        )
        charts = [
            {"chart_type": c.chart_type, "title": c.title, "x_axis": c.x_axis, "series": c.series}
            for c in decision.charts
        ]

        return MedicalAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            total_score=score.total_score if score else 0.0,
            level=score.level if score else "待评估",
            dimensions=dimensions,
            strengths=score.strengths if score else [],
            weaknesses=score.weaknesses if score else [],
            charts=charts,
            evidence=evidence_items,
            warnings=decision.warnings,
            data_missing=decision.data_missing,
            suggestion=self._build_suggestion(score, decision.warnings),
        )

    def _build_suggestion(
        self,
        score: Any,
        warnings: list[str],
    ) -> str:
        # TODO: M2阶段实现基于评分的建议生成
        if warnings:
            return f"注意：{'；'.join(warnings)}。建议补充数据后重新评估。"
        return "待实现：M2阶段补充基于评分的投资建议。"


__all__ = ["MedicalAnalyzer", "MedicalAnalysisResult"]
