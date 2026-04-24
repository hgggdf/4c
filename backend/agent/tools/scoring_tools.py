"""医药评分工具 - 10个维度评分机制骨架。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCORING_DIMENSIONS = [
    "财务质量",
    "研发实力",
    "管线价值",
    "审批进展",
    "临床风险",
    "回款风险",
    "医保管控风险",
    "商业化能力",
    "合规风险",
    "舆情风险",
]


@dataclass
class DimensionScore:
    name: str
    score: float  # 0-100
    weight: float  # 权重
    comment: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PharmaScoreResult:
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str  # 优秀/良好/一般/较差/差
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    data_missing: list[str] = field(default_factory=list)


class PharmaScorer:
    """医药公司综合评分引擎。"""

    _DIMENSION_WEIGHTS: dict[str, float] = {
        "财务质量": 0.15,
        "研发实力": 0.15,
        "管线价值": 0.15,
        "审批进展": 0.10,
        "临床风险": 0.10,
        "回款风险": 0.08,
        "医保管控风险": 0.08,
        "商业化能力": 0.08,
        "合规风险": 0.06,
        "舆情风险": 0.05,
    }

    _LEVEL_THRESHOLDS = [
        (85, "优秀"),
        (70, "良好"),
        (55, "一般"),
        (40, "较差"),
        (0,  "差"),
    ]

    def score(
        self,
        stock_code: str,
        stock_name: str,
        year: int,
        financial_data: dict[str, Any] | None = None,
        pipeline_data: dict[str, Any] | None = None,
    ) -> PharmaScoreResult:
        """计算综合评分，返回 PharmaScoreResult。"""
        # TODO: M2阶段实现各维度真实评分逻辑
        dimensions = self._score_all_dimensions(financial_data, pipeline_data)
        total_score = self._calc_total(dimensions)
        level = self._calc_level(total_score)
        strengths, weaknesses = self._extract_sw(dimensions)
        missing = self._detect_missing(financial_data, pipeline_data)

        return PharmaScoreResult(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            total_score=total_score,
            level=level,
            dimensions=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            data_missing=missing,
        )

    def _score_all_dimensions(
        self,
        financial_data: dict[str, Any] | None,
        pipeline_data: dict[str, Any] | None,
    ) -> list[DimensionScore]:
        results = []
        for dim in SCORING_DIMENSIONS:
            weight = self._DIMENSION_WEIGHTS[dim]
            # TODO: M2阶段替换为真实评分
            results.append(DimensionScore(name=dim, score=0.0, weight=weight, comment="待实现"))
        return results

    def _calc_total(self, dimensions: list[DimensionScore]) -> float:
        return sum(d.score * d.weight for d in dimensions)

    def _calc_level(self, total_score: float) -> str:
        for threshold, level in self._LEVEL_THRESHOLDS:
            if total_score >= threshold:
                return level
        return "差"

    def _extract_sw(self, dimensions: list[DimensionScore]) -> tuple[list[str], list[str]]:
        sorted_dims = sorted(dimensions, key=lambda d: d.score, reverse=True)
        strengths = [d.name for d in sorted_dims[:3] if d.score > 0]
        weaknesses = [d.name for d in sorted_dims[-3:] if d.score >= 0]
        return strengths, weaknesses

    def _detect_missing(
        self,
        financial_data: dict[str, Any] | None,
        pipeline_data: dict[str, Any] | None,
    ) -> list[str]:
        missing = []
        if not financial_data:
            missing.append("财务数据缺失")
        if not pipeline_data:
            missing.append("管线数据缺失")
        return missing


__all__ = ["PharmaScorer", "PharmaScoreResult", "DimensionScore", "SCORING_DIMENSIONS"]
