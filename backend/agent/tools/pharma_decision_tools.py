"""医药综合决策工具骨架 - 整合评分、图表、证据的复合工具。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .scoring_tools import PharmaScorer, PharmaScoreResult
from .chart_tools import PharmaChartBuilder, ChartConfig
from .evidence_tools import PharmaEvidenceCollector, EvidenceBundle


@dataclass
class PharmaDecisionResult:
    stock_code: str
    stock_name: str
    year: int
    score_result: PharmaScoreResult | None = None
    charts: list[ChartConfig] = field(default_factory=list)
    evidence: EvidenceBundle | None = None
    warnings: list[str] = field(default_factory=list)
    data_missing: list[str] = field(default_factory=list)


class PharmaDecisionTool:
    """医药综合决策复合工具，供 MedicalAnalyzer 调用。"""

    def __init__(self) -> None:
        self._scorer = PharmaScorer()
        self._chart_builder = PharmaChartBuilder()
        self._evidence_collector = PharmaEvidenceCollector()

    def analyze(
        self,
        stock_code: str,
        stock_name: str,
        year: int,
        query: str = "",
        financial_data: dict[str, Any] | None = None,
        pipeline_data: dict[str, Any] | None = None,
        raw_evidence: list[dict[str, Any]] | None = None,
    ) -> PharmaDecisionResult:
        """执行综合医药分析，返回 PharmaDecisionResult。"""
        # TODO: M2/M3阶段逐步填充真实逻辑
        score_result = self._scorer.score(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            financial_data=financial_data,
            pipeline_data=pipeline_data,
        )

        evidence = self._evidence_collector.collect(
            query=query,
            stock_code=stock_code,
            stock_name=stock_name,
            raw_items=raw_evidence,
        )

        charts: list[ChartConfig] = []
        # TODO: M3阶段补充图表构建

        warnings = self._build_warnings(score_result, evidence)
        missing = list({*score_result.data_missing, *evidence.missing_types})

        return PharmaDecisionResult(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            score_result=score_result,
            charts=charts,
            evidence=evidence,
            warnings=warnings,
            data_missing=missing,
        )

    def _build_warnings(
        self,
        score_result: PharmaScoreResult,
        evidence: EvidenceBundle,
    ) -> list[str]:
        # TODO: M3阶段实现完整预警规则
        warnings = []
        if score_result.data_missing:
            warnings.append(f"数据缺失：{'、'.join(score_result.data_missing)}")
        if evidence.missing_types:
            warnings.append(f"证据不足：缺少 {'、'.join(evidence.missing_types)} 类型")
        return warnings


__all__ = ["PharmaDecisionTool", "PharmaDecisionResult"]
