"""医药评分工具 - 10个维度评分机制。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
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
    score: float        # 0-100
    weight: float
    comment: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PharmaScoreResult:
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str          # 优秀/良好/一般/较差/差
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    data_missing: list[str] = field(default_factory=list)


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (f != f) else f  # NaN guard
    except (TypeError, ValueError):
        return None


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _score_higher_better(value: float, poor: float, avg: float, good: float) -> float:
    """越高越好的线性分段评分，返回 0-100。"""
    if value >= good:
        return _clamp(90 + min(10, (value - good) / (abs(good) + 1) * 10))
    if value >= avg:
        return 60 + (value - avg) / max(good - avg, 1e-6) * 30
    if value >= poor:
        return 30 + (value - poor) / max(avg - poor, 1e-6) * 30
    return _clamp(30 * value / max(abs(poor), 1e-6))


def _score_lower_better(value: float, good: float, avg: float, poor: float) -> float:
    """越低越好的线性分段评分，返回 0-100。"""
    if value <= good:
        return _clamp(90 + min(10, (good - value) / (abs(good) + 1) * 10))
    if value <= avg:
        return 60 + (avg - value) / max(avg - good, 1e-6) * 30
    if value <= poor:
        return 30 + (poor - value) / max(poor - avg, 1e-6) * 30
    return _clamp(30 * (2 * poor - value) / max(abs(poor), 1e-6))


class PharmaScorer:
    """医药公司综合评分引擎。"""

    _DIMENSION_WEIGHTS: dict[str, float] = {
        "财务质量":    0.15,
        "研发实力":    0.15,
        "管线价值":    0.15,
        "审批进展":    0.10,
        "临床风险":    0.10,
        "回款风险":    0.08,
        "医保管控风险": 0.08,
        "商业化能力":  0.08,
        "合规风险":    0.06,
        "舆情风险":    0.05,
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
        fd = financial_data or {}
        pd_ = pipeline_data or {}

        dimensions = [
            self._score_financial_quality(fd),
            self._score_rd_strength(fd),
            self._score_pipeline_value(pd_),
            self._score_approval_progress(pd_),
            self._score_clinical_risk(pd_),
            self._score_payment_risk(fd),
            self._score_insurance_risk(pd_),
            self._score_commercialization(fd),
            self._score_compliance_risk(pd_),
            self._score_sentiment_risk(pd_),
        ]

        total_score = round(sum(d.score * d.weight for d in dimensions), 1)
        level = self._calc_level(total_score)
        strengths = [d.name for d in sorted(dimensions, key=lambda d: d.score, reverse=True)[:3] if d.score >= 60]
        weaknesses = [d.name for d in sorted(dimensions, key=lambda d: d.score)[:3] if d.score < 50]
        missing = self._detect_missing(fd, pd_)

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

    # ── 各维度评分 ──────────────────────────────────────────────────────────

    def _score_financial_quality(self, fd: dict[str, Any]) -> DimensionScore:
        """财务质量：毛利率、净利率、ROE、资产负债率综合评分。"""
        weight = self._DIMENSION_WEIGHTS["财务质量"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        gross_margin = _to_float(fd.get("gross_margin"))
        if gross_margin is not None:
            s = _score_higher_better(gross_margin, poor=20, avg=45, good=65)
            scores.append(s)
            detail["毛利率"] = f"{gross_margin:.1f}%"

        net_margin = _to_float(fd.get("net_margin"))
        if net_margin is not None:
            s = _score_higher_better(net_margin, poor=5, avg=12, good=22)
            scores.append(s)
            detail["净利率"] = f"{net_margin:.1f}%"

        roe = _to_float(fd.get("roe"))
        if roe is not None:
            s = _score_higher_better(roe, poor=5, avg=12, good=20)
            scores.append(s)
            detail["ROE"] = f"{roe:.1f}%"

        debt_ratio = _to_float(fd.get("debt_ratio"))
        if debt_ratio is not None:
            s = _score_lower_better(debt_ratio, good=25, avg=45, poor=65)
            scores.append(s)
            detail["资产负债率"] = f"{debt_ratio:.1f}%"

        revenue_growth = _to_float(fd.get("revenue_growth"))
        if revenue_growth is not None:
            s = _score_higher_better(revenue_growth, poor=0, avg=10, good=25)
            scores.append(s)
            detail["营收增速"] = f"{revenue_growth:.1f}%"

        if not scores:
            return DimensionScore(name="财务质量", score=50.0, weight=weight,
                                  comment="财务数据不足，使用中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("财务质量", avg_score, detail)
        return DimensionScore(name="财务质量", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_rd_strength(self, fd: dict[str, Any]) -> DimensionScore:
        """研发实力：研发费用率、研发费用绝对值趋势。"""
        weight = self._DIMENSION_WEIGHTS["研发实力"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        rd_ratio = _to_float(fd.get("rd_ratio"))
        if rd_ratio is not None:
            # 医药行业研发费用率：<5%差，8%均值，15%优秀，20%+顶尖
            s = _score_higher_better(rd_ratio, poor=5, avg=8, good=15)
            scores.append(s)
            detail["研发费用率"] = f"{rd_ratio:.1f}%"

        rd_growth = _to_float(fd.get("rd_growth"))
        if rd_growth is not None:
            s = _score_higher_better(rd_growth, poor=-5, avg=10, good=25)
            scores.append(s)
            detail["研发费用增速"] = f"{rd_growth:.1f}%"

        # 药品审批数量作为研发产出代理指标
        approval_count = fd.get("approval_count_innovative")
        if approval_count is not None:
            cnt = int(approval_count)
            s = min(100.0, 40 + cnt * 15.0)  # 每个创新药审批+15分，上限100
            scores.append(s)
            detail["创新药审批数"] = cnt

        if not scores:
            return DimensionScore(name="研发实力", score=50.0, weight=weight,
                                  comment="研发数据不足，使用中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("研发实力", avg_score, detail)
        return DimensionScore(name="研发实力", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_pipeline_value(self, pd_: dict[str, Any]) -> DimensionScore:
        """管线价值：在研药物数量、阶段分布、创新药占比。"""
        weight = self._DIMENSION_WEIGHTS["管线价值"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        total_pipeline = _to_float(pd_.get("pipeline_total"))
        if total_pipeline is not None:
            # 管线总数：<5个差，10个均值，20+优秀
            s = _score_higher_better(total_pipeline, poor=5, avg=10, good=20)
            scores.append(s)
            detail["管线总数"] = int(total_pipeline)

        phase3_count = _to_float(pd_.get("pipeline_phase3"))
        if phase3_count is not None:
            s = _score_higher_better(phase3_count, poor=0, avg=2, good=5)
            scores.append(s * 1.2)  # III期权重更高
            detail["III期数量"] = int(phase3_count)

        innovative_ratio = _to_float(pd_.get("innovative_drug_ratio"))
        if innovative_ratio is not None:
            s = _score_higher_better(innovative_ratio * 100, poor=10, avg=30, good=60)
            scores.append(s)
            detail["创新药占比"] = f"{innovative_ratio * 100:.1f}%"

        if not scores:
            return DimensionScore(name="管线价值", score=50.0, weight=weight,
                                  comment="管线数据不足，使用中性评分", raw_data=detail)

        avg_score = _clamp(round(sum(scores) / len(scores), 1))
        comment = self._comment("管线价值", avg_score, detail)
        return DimensionScore(name="管线价值", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_approval_progress(self, pd_: dict[str, Any]) -> DimensionScore:
        """审批进展：近期获批数量、审批类型质量。"""
        weight = self._DIMENSION_WEIGHTS["审批进展"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        recent_approvals = _to_float(pd_.get("recent_approvals"))
        if recent_approvals is not None:
            s = _score_higher_better(recent_approvals, poor=0, avg=1, good=3)
            scores.append(s)
            detail["近期获批数"] = int(recent_approvals)

        innovative_approvals = _to_float(pd_.get("innovative_approvals"))
        if innovative_approvals is not None:
            s = min(100.0, 50 + innovative_approvals * 20)
            scores.append(s)
            detail["创新药获批数"] = int(innovative_approvals)

        pending_review = _to_float(pd_.get("pending_review_count"))
        if pending_review is not None:
            # 在审数量越多，潜在价值越高
            s = _score_higher_better(pending_review, poor=0, avg=2, good=5)
            scores.append(s * 0.7)  # 在审不如已批，权重打折
            detail["在审数量"] = int(pending_review)

        if not scores:
            return DimensionScore(name="审批进展", score=50.0, weight=weight,
                                  comment="审批数据不足，使用中性评分", raw_data=detail)

        avg_score = _clamp(round(sum(scores) / len(scores), 1))
        comment = self._comment("审批进展", avg_score, detail)
        return DimensionScore(name="审批进展", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_clinical_risk(self, pd_: dict[str, Any]) -> DimensionScore:
        """临床风险：临床失败率、中止事件数量（越低越好）。"""
        weight = self._DIMENSION_WEIGHTS["临床风险"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        trial_failures = _to_float(pd_.get("trial_failures"))
        if trial_failures is not None:
            # 临床失败/中止越少越好
            s = _score_lower_better(trial_failures, good=0, avg=1, poor=3)
            scores.append(s)
            detail["临床失败/中止数"] = int(trial_failures)

        phase3_failures = _to_float(pd_.get("phase3_failures"))
        if phase3_failures is not None:
            # III期失败影响更大
            s = _score_lower_better(phase3_failures, good=0, avg=1, poor=2)
            scores.append(s * 1.5)
            detail["III期失败数"] = int(phase3_failures)

        active_trials = _to_float(pd_.get("active_trials"))
        if active_trials is not None:
            # 在研临床数量多是正面信号（此维度反向：风险低=分高）
            s = _score_higher_better(active_trials, poor=1, avg=5, good=10)
            scores.append(s * 0.5)
            detail["在研临床数"] = int(active_trials)

        if not scores:
            return DimensionScore(name="临床风险", score=60.0, weight=weight,
                                  comment="临床数据不足，使用偏乐观中性评分", raw_data=detail)

        avg_score = _clamp(round(sum(scores) / len(scores), 1))
        comment = self._comment("临床风险", avg_score, detail)
        return DimensionScore(name="临床风险", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_payment_risk(self, fd: dict[str, Any]) -> DimensionScore:
        """回款风险：应收账款占比、现金流质量。"""
        weight = self._DIMENSION_WEIGHTS["回款风险"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        ar_ratio = _to_float(fd.get("ar_ratio"))  # 应收/营收
        if ar_ratio is not None:
            # 应收账款占营收比：<15%好，30%均值，50%+差
            s = _score_lower_better(ar_ratio * 100, good=15, avg=30, poor=50)
            scores.append(s)
            detail["应收账款占比"] = f"{ar_ratio * 100:.1f}%"

        cashflow_quality = _to_float(fd.get("cashflow_quality"))  # 经营现金流/净利润
        if cashflow_quality is not None:
            # 现金流质量：>1.2优秀，0.8均值，<0.5差
            s = _score_higher_better(cashflow_quality, poor=0.5, avg=0.8, good=1.2)
            scores.append(s)
            detail["现金流质量"] = f"{cashflow_quality:.2f}"

        operating_cashflow = _to_float(fd.get("operating_cashflow"))
        if operating_cashflow is not None and operating_cashflow > 0:
            scores.append(70.0)  # 经营现金流为正，基础分
            detail["经营现金流"] = "正值"
        elif operating_cashflow is not None and operating_cashflow <= 0:
            scores.append(20.0)
            detail["经营现金流"] = "负值"

        if not scores:
            return DimensionScore(name="回款风险", score=50.0, weight=weight,
                                  comment="回款数据不足，使用中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("回款风险", avg_score, detail)
        return DimensionScore(name="回款风险", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_insurance_risk(self, pd_: dict[str, Any]) -> DimensionScore:
        """医保管控风险：集采降价幅度、中标情况。"""
        weight = self._DIMENSION_WEIGHTS["医保管控风险"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        avg_price_cut = _to_float(pd_.get("avg_price_cut_ratio"))  # 平均降价幅度，正数表示降价
        if avg_price_cut is not None:
            # 降价幅度：<20%影响小，50%均值，>80%严重
            s = _score_lower_better(avg_price_cut * 100, good=20, avg=50, poor=80)
            scores.append(s)
            detail["平均集采降价幅度"] = f"{avg_price_cut * 100:.1f}%"

        procurement_failures = _to_float(pd_.get("procurement_failures"))
        if procurement_failures is not None:
            # 集采落标次数越少越好
            s = _score_lower_better(procurement_failures, good=0, avg=1, poor=3)
            scores.append(s)
            detail["集采落标次数"] = int(procurement_failures)

        procurement_wins = _to_float(pd_.get("procurement_wins"))
        if procurement_wins is not None:
            # 中标是正面信号（保量）
            s = _score_higher_better(procurement_wins, poor=0, avg=1, good=3)
            scores.append(s * 0.6)
            detail["集采中标次数"] = int(procurement_wins)

        if not scores:
            return DimensionScore(name="医保管控风险", score=60.0, weight=weight,
                                  comment="集采数据不足，使用偏乐观中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("医保管控风险", avg_score, detail)
        return DimensionScore(name="医保管控风险", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_commercialization(self, fd: dict[str, Any]) -> DimensionScore:
        """商业化能力：营收规模、销售费用率、业务多元化。"""
        weight = self._DIMENSION_WEIGHTS["商业化能力"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        revenue = _to_float(fd.get("revenue"))
        if revenue is not None:
            # 营收（亿元）：<5亿差，20亿均值，100亿+优秀
            revenue_yi = revenue / 1e8
            s = _score_higher_better(revenue_yi, poor=5, avg=20, good=100)
            scores.append(s)
            detail["营收规模"] = f"{revenue_yi:.1f}亿"

        selling_ratio = _to_float(fd.get("selling_ratio"))  # 销售费用/营收
        if selling_ratio is not None:
            # 销售费用率：医药行业偏高，>40%过高，25%均值，<15%精简
            s = _score_lower_better(selling_ratio * 100, good=15, avg=25, poor=40)
            scores.append(s)
            detail["销售费用率"] = f"{selling_ratio * 100:.1f}%"

        revenue_growth = _to_float(fd.get("revenue_growth"))
        if revenue_growth is not None:
            s = _score_higher_better(revenue_growth, poor=0, avg=10, good=25)
            scores.append(s)
            detail["营收增速"] = f"{revenue_growth:.1f}%"

        segment_count = _to_float(fd.get("segment_count"))
        if segment_count is not None:
            # 业务多元化：1个单一，3个均值，5+多元
            s = _score_higher_better(segment_count, poor=1, avg=3, good=5)
            scores.append(s * 0.5)
            detail["业务线数量"] = int(segment_count)

        if not scores:
            return DimensionScore(name="商业化能力", score=50.0, weight=weight,
                                  comment="商业化数据不足，使用中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("商业化能力", avg_score, detail)
        return DimensionScore(name="商业化能力", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_compliance_risk(self, pd_: dict[str, Any]) -> DimensionScore:
        """合规风险：监管处罚次数、风险等级。"""
        weight = self._DIMENSION_WEIGHTS["合规风险"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        high_risk_events = _to_float(pd_.get("regulatory_high_risk"))
        if high_risk_events is not None:
            s = _score_lower_better(high_risk_events, good=0, avg=1, poor=2)
            scores.append(s)
            detail["高风险监管事件"] = int(high_risk_events)

        total_risk_events = _to_float(pd_.get("regulatory_total"))
        if total_risk_events is not None:
            s = _score_lower_better(total_risk_events, good=0, avg=2, poor=5)
            scores.append(s * 0.7)
            detail["监管事件总数"] = int(total_risk_events)

        if not scores:
            return DimensionScore(name="合规风险", score=75.0, weight=weight,
                                  comment="无监管事件记录，合规状况良好", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("合规风险", avg_score, detail)
        return DimensionScore(name="合规风险", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    def _score_sentiment_risk(self, pd_: dict[str, Any]) -> DimensionScore:
        """舆情风险：新闻情感倾向、负面新闻占比。"""
        weight = self._DIMENSION_WEIGHTS["舆情风险"]
        scores: list[float] = []
        detail: dict[str, Any] = {}

        sentiment_score = _to_float(pd_.get("sentiment_score"))  # -1到1，越高越正面
        if sentiment_score is not None:
            # 转换到0-100：-1→0, 0→50, 1→100
            s = _clamp((sentiment_score + 1) / 2 * 100)
            scores.append(s)
            detail["情感得分"] = f"{sentiment_score:.2f}"

        negative_ratio = _to_float(pd_.get("negative_news_ratio"))
        if negative_ratio is not None:
            s = _score_lower_better(negative_ratio * 100, good=10, avg=30, poor=60)
            scores.append(s)
            detail["负面新闻占比"] = f"{negative_ratio * 100:.1f}%"

        high_impact_negative = _to_float(pd_.get("high_impact_negative"))
        if high_impact_negative is not None:
            s = _score_lower_better(high_impact_negative, good=0, avg=1, poor=3)
            scores.append(s)
            detail["高影响负面事件"] = int(high_impact_negative)

        if not scores:
            return DimensionScore(name="舆情风险", score=65.0, weight=weight,
                                  comment="舆情数据不足，使用偏乐观中性评分", raw_data=detail)

        avg_score = round(sum(scores) / len(scores), 1)
        comment = self._comment("舆情风险", avg_score, detail)
        return DimensionScore(name="舆情风险", score=avg_score, weight=weight,
                              comment=comment, raw_data=detail)

    # ── 工具方法 ────────────────────────────────────────────────────────────

    def _calc_level(self, total_score: float) -> str:
        for threshold, level in self._LEVEL_THRESHOLDS:
            if total_score >= threshold:
                return level
        return "差"

    def _comment(self, dim: str, score: float, detail: dict[str, Any]) -> str:
        level = "优秀" if score >= 80 else "良好" if score >= 65 else "一般" if score >= 50 else "偏弱"
        parts = [f"{k}:{v}" for k, v in list(detail.items())[:3]]
        suffix = f"（{'、'.join(parts)}）" if parts else ""
        return f"{dim}处于{level}水平（{score:.0f}分）{suffix}"

    def _detect_missing(self, fd: dict[str, Any], pd_: dict[str, Any]) -> list[str]:
        missing = []
        fin_keys = ["gross_margin", "net_margin", "roe", "debt_ratio", "revenue"]
        if not any(fd.get(k) is not None for k in fin_keys):
            missing.append("财务数据缺失")
        pipe_keys = ["pipeline_total", "recent_approvals", "trial_failures"]
        if not any(pd_.get(k) is not None for k in pipe_keys):
            missing.append("管线/公告数据缺失")
        if not pd_.get("sentiment_score") and not pd_.get("negative_news_ratio"):
            missing.append("舆情数据缺失")
        return missing


__all__ = ["PharmaScorer", "PharmaScoreResult", "DimensionScore", "SCORING_DIMENSIONS"]
