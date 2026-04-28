"""医药综合决策工具 - 整合评分、图表、证据，实现完整预警规则。"""

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


# 预警阈值常量
_WARN_SCORE_DIM_LOW = 40        # 单维度低于此分触发红色预警
_WARN_SCORE_DIM_MEDIUM = 55     # 单维度低于此分触发黄色预警
_WARN_TOTAL_LOW = 45            # 总分低于此分触发整体预警
_WARN_DEBT_RATIO_HIGH = 60.0    # 资产负债率高风险线（%）
_WARN_AR_RATIO_HIGH = 0.40      # 应收账款占比高风险线
_WARN_PRICE_CUT_SEVERE = 0.60   # 集采降价超过60%触发预警
_WARN_PHASE3_FAIL = 1           # III期失败数触发预警阈值
_WARN_REG_HIGH_RISK = 1         # 高风险监管事件数触发预警阈值
_WARN_NEG_NEWS_RATIO = 0.50     # 负面新闻占比超过50%触发预警


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
        financial_trends: list[dict[str, Any]] | None = None,
        pipeline_stages: list[dict[str, Any]] | None = None,
    ) -> PharmaDecisionResult:
        fd = financial_data or {}
        pd_ = pipeline_data or {}

        score_result = self._scorer.score(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            financial_data=fd,
            pipeline_data=pd_,
        )

        evidence = self._evidence_collector.collect(
            query=query,
            stock_code=stock_code,
            stock_name=stock_name,
            raw_items=raw_evidence,
        )

        dim_dicts = [
            {"name": d.name, "score": d.score, "weight": d.weight}
            for d in score_result.dimensions
        ]
        charts = self._chart_builder.build_from_score_result(
            dimensions=dim_dicts,
            financial_trends=financial_trends or [],
            pipeline_stages=pipeline_stages or [],
            stock_name=stock_name,
        )

        warnings = self._build_warnings(score_result, evidence, fd, pd_)
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

    # ── 预警规则 ─────────────────────────────────────────────────────────────

    def _build_warnings(
        self,
        score_result: PharmaScoreResult,
        evidence: EvidenceBundle,
        fd: dict[str, Any],
        pd_: dict[str, Any],
    ) -> list[str]:
        warnings: list[str] = []

        # 1. 数据缺失预警
        if score_result.data_missing:
            warnings.append(f"【数据缺失】{'、'.join(score_result.data_missing)}，评分结果仅供参考")

        # 2. 证据不足预警
        if evidence.missing_types:
            warnings.append(f"【证据不足】缺少 {'、'.join(evidence.missing_types)} 类型证据，建议补充后重新分析")

        # 3. 总分过低预警
        if score_result.total_score < _WARN_TOTAL_LOW:
            warnings.append(
                f"【整体风险】综合评分 {score_result.total_score:.0f} 分（{score_result.level}），"
                f"整体基本面偏弱，建议谨慎"
            )

        # 4. 单维度红色预警（<40分）
        for dim in score_result.dimensions:
            if dim.score < _WARN_SCORE_DIM_LOW:
                warnings.append(f"【高风险】{dim.name} 得分 {dim.score:.0f} 分，存在重大风险")

        # 5. 单维度黄色预警（40-55分）
        for dim in score_result.dimensions:
            if _WARN_SCORE_DIM_LOW <= dim.score < _WARN_SCORE_DIM_MEDIUM:
                warnings.append(f"【关注】{dim.name} 得分 {dim.score:.0f} 分，需持续跟踪")

        # 6. 财务专项预警
        warnings.extend(self._financial_warnings(fd))

        # 7. 管线/临床专项预警
        warnings.extend(self._pipeline_warnings(pd_))

        # 8. 合规专项预警
        warnings.extend(self._compliance_warnings(pd_))

        # 9. 舆情专项预警
        warnings.extend(self._sentiment_warnings(pd_))

        return warnings

    def _financial_warnings(self, fd: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        debt_ratio = _to_float(fd.get("debt_ratio"))
        if debt_ratio is not None and debt_ratio >= _WARN_DEBT_RATIO_HIGH:
            level = "高" if debt_ratio >= 70 else "中"
            warnings.append(
                f"【{level}风险-财务】资产负债率 {debt_ratio:.1f}%，"
                f"{'偿债压力较大，需关注流动性' if debt_ratio >= 70 else '负债水平偏高，建议关注债务结构'}"
            )

        ar_ratio = _to_float(fd.get("ar_ratio"))
        if ar_ratio is not None and ar_ratio >= _WARN_AR_RATIO_HIGH:
            warnings.append(
                f"【中风险-回款】应收账款占营收比 {ar_ratio * 100:.1f}%，"
                f"回款风险较高，建议关注账期管理"
            )

        ocf = _to_float(fd.get("operating_cashflow"))
        np_ = _to_float(fd.get("net_profit"))
        if ocf is not None and np_ is not None and np_ > 0 and ocf < 0:
            warnings.append("【中风险-现金流】净利润为正但经营现金流为负，盈利质量存疑")

        revenue_growth = _to_float(fd.get("revenue_growth"))
        if revenue_growth is not None and revenue_growth < -10:
            warnings.append(
                f"【高风险-成长性】营收同比下滑 {abs(revenue_growth):.1f}%，"
                f"业务萎缩信号明显"
            )

        return warnings

    def _pipeline_warnings(self, pd_: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        phase3_failures = _to_float(pd_.get("phase3_failures"))
        if phase3_failures is not None and phase3_failures >= _WARN_PHASE3_FAIL:
            warnings.append(
                f"【高风险-临床】近期 {int(phase3_failures)} 个 III 期临床失败/中止，"
                f"管线价值受损，需重新评估"
            )

        avg_cut = _to_float(pd_.get("avg_price_cut_ratio"))
        if avg_cut is not None and avg_cut >= _WARN_PRICE_CUT_SEVERE:
            warnings.append(
                f"【高风险-集采】集采平均降价幅度 {avg_cut * 100:.0f}%，"
                f"核心产品盈利能力受到严重压缩"
            )

        pipeline_total = _to_float(pd_.get("pipeline_total"))
        if pipeline_total is not None and pipeline_total < 3:
            warnings.append("【中风险-管线】在研管线产品数量不足3个，未来增长动力有限")

        return warnings

    def _compliance_warnings(self, pd_: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        high_risk = _to_float(pd_.get("regulatory_high_risk"))
        if high_risk is not None and high_risk >= _WARN_REG_HIGH_RISK:
            warnings.append(
                f"【高风险-合规】近期 {int(high_risk)} 起高风险监管事件，"
                f"合规风险显著，建议密切跟踪后续处理结果"
            )

        total_risk = _to_float(pd_.get("regulatory_total"))
        if total_risk is not None and total_risk >= 3 and (high_risk or 0) == 0:
            warnings.append(
                f"【中风险-合规】近期共 {int(total_risk)} 起监管事件，"
                f"虽无高风险事件，仍需关注合规态势"
            )

        return warnings

    def _sentiment_warnings(self, pd_: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        neg_ratio = _to_float(pd_.get("negative_news_ratio"))
        if neg_ratio is not None and neg_ratio >= _WARN_NEG_NEWS_RATIO:
            warnings.append(
                f"【中风险-舆情】负面新闻占比 {neg_ratio * 100:.0f}%，"
                f"市场情绪偏负面，短期股价可能承压"
            )

        high_neg = _to_float(pd_.get("high_impact_negative"))
        if high_neg is not None and high_neg >= 2:
            warnings.append(
                f"【高风险-舆情】{int(high_neg)} 条高影响力负面事件，"
                f"舆情风险较高，建议关注事件进展"
            )

        return warnings


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


__all__ = ["PharmaDecisionTool", "PharmaDecisionResult"]
