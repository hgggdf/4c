"""医药分析引擎 - M3阶段：接入图表、证据、完整预警规则。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from agent.tools.pharma_decision_tools import PharmaDecisionTool, PharmaDecisionResult
from agent.tools.scoring_tools import PharmaScorer, PharmaScoreResult

logger = logging.getLogger(__name__)


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


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _ratio(num: Any, den: Any) -> float | None:
    n, d = _to_float(num), _to_float(den)
    if n is None or d in (None, 0.0):
        return None
    return n / d


class MedicalAnalyzer:
    """
    医药分析引擎，供 glm_agent.py 调用。

    用法：
        analyzer = MedicalAnalyzer()
        with container.ctx.session() as db:
            result = analyzer.analyze(db, stock_code, stock_name, year, query)
    """

    def __init__(self) -> None:
        self._scorer = PharmaScorer()
        self._decision_tool = PharmaDecisionTool()

    # ── 主入口 ──────────────────────────────────────────────────────────────

    def analyze(
        self,
        db: Session,
        stock_code: str,
        stock_name: str,
        year: int,
        query: str = "",
        raw_evidence: list[dict[str, Any]] | None = None,
    ) -> MedicalAnalysisResult:
        financial_data = self._load_financial_data(db, stock_code, year)
        pipeline_data = self._load_pipeline_data(db, stock_code)

        score_result: PharmaScoreResult = self._scorer.score(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            financial_data=financial_data,
            pipeline_data=pipeline_data,
        )

        financial_trends = self._load_financial_trends(db, stock_code)
        pipeline_stages = self._load_pipeline_stages(db, stock_code)

        decision: PharmaDecisionResult = self._decision_tool.analyze(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            query=query,
            financial_data=financial_data,
            pipeline_data=pipeline_data,
            raw_evidence=raw_evidence,
            financial_trends=financial_trends,
            pipeline_stages=pipeline_stages,
        )

        dimensions = [
            {
                "name": d.name,
                "score": d.score,
                "weight": d.weight,
                "comment": d.comment,
            }
            for d in score_result.dimensions
        ]
        evidence_items = (
            [
                {
                    "kind": e.kind,
                    "title": e.title,
                    "date": e.date,
                    "source": e.source,
                    "summary": e.summary,
                    "relevance": e.relevance,
                    "tags": e.tags,
                }
                for e in decision.evidence.items
            ]
            if decision.evidence
            else []
        )
        charts = [
            {
                "chart_type": c.chart_type,
                "title": c.title,
                "x_axis": c.x_axis,
                "series": c.series,
                "extra": c.extra,
            }
            for c in decision.charts
        ]
        missing = list({*score_result.data_missing, *decision.data_missing})
        warnings = list(dict.fromkeys(decision.warnings))  # 去重保序

        return MedicalAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            year=year,
            total_score=score_result.total_score,
            level=score_result.level,
            dimensions=dimensions,
            strengths=score_result.strengths,
            weaknesses=score_result.weaknesses,
            charts=charts,
            evidence=evidence_items,
            warnings=warnings,
            data_missing=missing,
            suggestion=self._build_suggestion(score_result, warnings),
        )

    # ── 财务数据加载 ─────────────────────────────────────────────────────────

    def _load_financial_data(self, db: Session, stock_code: str, year: int) -> dict[str, Any]:
        """从热表拉取财务快照，组装 scoring_tools 所需字段。"""
        from sqlalchemy import select
        from app.core.database.models.financial_hot import (
            IncomeStatementHot,
            BalanceSheetHot,
            CashflowStatementHot,
            FinancialMetricHot,
            BusinessSegmentHot,
        )

        try:
            incomes = db.execute(
                select(IncomeStatementHot)
                .where(IncomeStatementHot.stock_code == stock_code)
                .order_by(IncomeStatementHot.report_date.desc())
                .limit(4)
            ).scalars().all()

            balances = db.execute(
                select(BalanceSheetHot)
                .where(BalanceSheetHot.stock_code == stock_code)
                .order_by(BalanceSheetHot.report_date.desc())
                .limit(4)
            ).scalars().all()

            cashflows = db.execute(
                select(CashflowStatementHot)
                .where(CashflowStatementHot.stock_code == stock_code)
                .order_by(CashflowStatementHot.report_date.desc())
                .limit(4)
            ).scalars().all()

            metrics = db.execute(
                select(FinancialMetricHot)
                .where(FinancialMetricHot.stock_code == stock_code)
                .order_by(FinancialMetricHot.report_date.desc())
                .limit(40)
            ).scalars().all()

            segments = db.execute(
                select(BusinessSegmentHot)
                .where(BusinessSegmentHot.stock_code == stock_code)
                .order_by(BusinessSegmentHot.report_date.desc())
                .limit(20)
            ).scalars().all()

        except Exception as exc:
            logger.warning("financial data load failed for %s: %s", stock_code, exc)
            return

        # 取目标年份或最近年份的记录
        income = self._pick_year(incomes, year)
        balance = self._pick_year(balances, year)
        cashflow = self._pick_year(cashflows, year)
        metric_map = self._build_metric_map(metrics, year)

        fd: dict[str, Any] = {}

        # 毛利率
        gm = _to_float(metric_map.get("gross_margin"))
        if gm is None:
            gm = _ratio(
                getattr(income, "gross_profit", None),
                getattr(income, "revenue", None),
            )
            if gm is not None:
                gm *= 100
        fd["gross_margin"] = gm

        # 净利率
        nm = _to_float(metric_map.get("net_margin"))
        if nm is None:
            nm = _ratio(
                getattr(income, "net_profit", None),
                getattr(income, "revenue", None),
            )
            if nm is not None:
                nm *= 100
        fd["net_margin"] = nm

        # ROE
        roe = _to_float(metric_map.get("roe"))
        if roe is None:
            roe = _ratio(
                getattr(income, "net_profit", None),
                getattr(balance, "equity", None),
            )
            if roe is not None:
                roe *= 100
        fd["roe"] = roe

        # 资产负债率
        dr = _to_float(metric_map.get("debt_ratio"))
        if dr is None:
            dr = _ratio(
                getattr(balance, "total_liabilities", None),
                getattr(balance, "total_assets", None),
            )
            if dr is not None:
                dr *= 100
        fd["debt_ratio"] = dr

        # 研发费用率
        rd = _to_float(metric_map.get("rd_ratio"))
        if rd is None:
            rd = _ratio(
                getattr(income, "rd_expense", None),
                getattr(income, "revenue", None),
            )
            if rd is not None:
                rd *= 100
        fd["rd_ratio"] = rd

        # 营收
        fd["revenue"] = _to_float(getattr(income, "revenue", None))

        # 营收增速（与上一年对比）
        prev_income = self._pick_year(incomes, year - 1)
        if income and prev_income:
            fd["revenue_growth"] = _ratio(
                _to_float(getattr(income, "revenue", None)) - _to_float(getattr(prev_income, "revenue", None)),
                getattr(prev_income, "revenue", None),
            )
            if fd["revenue_growth"] is not None:
                fd["revenue_growth"] *= 100

        # 研发费用增速
        if income and prev_income:
            rd_curr = _to_float(getattr(income, "rd_expense", None))
            rd_prev = _to_float(getattr(prev_income, "rd_expense", None))
            if rd_curr is not None and rd_prev and rd_prev != 0:
                fd["rd_growth"] = (rd_curr - rd_prev) / abs(rd_prev) * 100

        # 应收账款占比
        ar = _to_float(getattr(balance, "accounts_receivable", None))
        rev = _to_float(getattr(income, "revenue", None))
        fd["ar_ratio"] = _ratio(ar, rev)

        # 现金流质量（经营现金流 / 净利润）
        ocf = _to_float(getattr(cashflow, "operating_cashflow", None))
        np_ = _to_float(getattr(income, "net_profit", None))
        fd["operating_cashflow"] = ocf
        fd["cashflow_quality"] = _ratio(ocf, np_)

        # 销售费用率
        fd["selling_ratio"] = _ratio(
            getattr(income, "selling_expense", None),
            getattr(income, "revenue", None),
        )

        # 业务线数量
        if segments:
            recent_date = max((s.report_date for s in segments), default=None)
            if recent_date:
                fd["segment_count"] = len({s.segment_name for s in segments if s.report_date == recent_date})

        return {k: v for k, v in fd.items() if v is not None}

    # ── 图表数据加载 ─────────────────────────────────────────────────────────

    def _load_financial_trends(self, db: Session, stock_code: str) -> list[dict[str, Any]]:
        """加载财务趋势数据，供图表构建器使用。"""
        from sqlalchemy import select
        from app.core.database.models.financial_hot import IncomeStatementHot

        try:
            incomes = db.execute(
                select(IncomeStatementHot)
                .where(IncomeStatementHot.stock_code == stock_code)
                .order_by(IncomeStatementHot.report_date.asc())
                .limit(8)
            ).scalars().all()
        except Exception:
            return []

        if not incomes:
            return []

        revenue_points = []
        profit_points = []
        for row in incomes:
            year = int(row.fiscal_year or row.report_date.year)
            rev = _to_float(row.revenue)
            np_ = _to_float(row.net_profit)
            if rev is not None:
                revenue_points.append({"year": year, "value": round(rev / 1e8, 2), "unit": "亿元"})
            if np_ is not None:
                profit_points.append({"year": year, "value": round(np_ / 1e8, 2), "unit": "亿元"})

        trends = []
        if revenue_points:
            trends.append({"metric": "营业总收入", "points": revenue_points})
        if profit_points:
            trends.append({"metric": "净利润", "points": profit_points})
        return trends

    def _load_pipeline_stages(self, db: Session, stock_code: str) -> list[dict[str, Any]]:
        """加载管线阶段分布数据，供图表构建器使用。"""
        from sqlalchemy import select
        from app.core.database.models.announcement_hot import DrugApprovalHot, ClinicalTrialEventHot

        try:
            approvals = db.execute(
                select(DrugApprovalHot)
                .where(DrugApprovalHot.stock_code == stock_code)
                .limit(100)
            ).scalars().all()

            trials = db.execute(
                select(ClinicalTrialEventHot)
                .where(ClinicalTrialEventHot.stock_code == stock_code)
                .limit(100)
            ).scalars().all()
        except Exception:
            return []

        stage_map: dict[str, dict[str, int]] = {}

        for a in approvals:
            stage = str(a.drug_stage or "其他").strip() or "其他"
            bucket = stage_map.setdefault(stage, {"count": 0, "innovative": 0})
            bucket["count"] += 1
            if a.is_innovative_drug:
                bucket["innovative"] += 1

        # 临床阶段补充（按 trial_phase 归类）
        phase_order = ["I期", "II期", "III期", "NDA", "上市"]
        for t in trials:
            phase = str(t.trial_phase or "").strip()
            if not phase:
                continue
            # 标准化阶段名
            for p in phase_order:
                if p in phase:
                    phase = p
                    break
            bucket = stage_map.setdefault(phase, {"count": 0, "innovative": 0})
            # 避免与 approval 重复计数：只在 stage_map 中没有该药名时才加
            bucket["count"] = max(bucket["count"], 1)

        if not stage_map:
            return []

        # 按预设顺序排列
        ordered = []
        for stage in phase_order:
            if stage in stage_map:
                ordered.append({"stage": stage, **stage_map.pop(stage)})
        for stage, data in stage_map.items():
            ordered.append({"stage": stage, **data})
        return ordered

    # ── 管线/公告/舆情数据加载 ───────────────────────────────────────────────

    def _load_pipeline_data(self, db: Session, stock_code: str) -> dict[str, Any]:
        """从公告热表和新闻热表拉取管线、审批、临床、集采、合规、舆情数据。"""
        from sqlalchemy import select
        from app.core.database.models.announcement_hot import (
            DrugApprovalHot,
            ClinicalTrialEventHot,
            CentralizedProcurementEventHot,
            RegulatoryRiskEventHot,
        )
        from app.core.database.models.news_hot import NewsCompanyMapHot, NewsRawHot

        pd_: dict[str, Any] = {}

        try:
            approvals = db.execute(
                select(DrugApprovalHot)
                .where(DrugApprovalHot.stock_code == stock_code)
                .order_by(DrugApprovalHot.approval_date.desc())
                .limit(50)
            ).scalars().all()

            trials = db.execute(
                select(ClinicalTrialEventHot)
                .where(ClinicalTrialEventHot.stock_code == stock_code)
                .order_by(ClinicalTrialEventHot.event_date.desc())
                .limit(50)
            ).scalars().all()

            procurements = db.execute(
                select(CentralizedProcurementEventHot)
                .where(CentralizedProcurementEventHot.stock_code == stock_code)
                .order_by(CentralizedProcurementEventHot.event_date.desc())
                .limit(30)
            ).scalars().all()

            reg_risks = db.execute(
                select(RegulatoryRiskEventHot)
                .where(RegulatoryRiskEventHot.stock_code == stock_code)
                .order_by(RegulatoryRiskEventHot.event_date.desc())
                .limit(20)
            ).scalars().all()

            news_maps = db.execute(
                select(NewsCompanyMapHot, NewsRawHot)
                .join(NewsRawHot, NewsCompanyMapHot.news_id == NewsRawHot.id)
                .where(NewsCompanyMapHot.stock_code == stock_code)
                .order_by(NewsRawHot.publish_time.desc())
                .limit(30)
            ).all()

        except Exception as exc:
            logger.warning("pipeline data load failed for %s: %s", stock_code, exc)
            return {}

        # ── 管线价值 ──
        innovative_count = sum(1 for a in approvals if a.is_innovative_drug)
        total_pipeline = len({a.drug_name for a in approvals if a.drug_name})
        pd_["pipeline_total"] = total_pipeline
        pd_["approval_count_innovative"] = innovative_count
        pd_["innovative_drug_ratio"] = innovative_count / total_pipeline if total_pipeline else None

        # ── 审批进展 ──
        from datetime import date, timedelta
        cutoff_1y = date.today() - timedelta(days=365)
        recent_approvals = [a for a in approvals if a.approval_date and a.approval_date >= cutoff_1y]
        pd_["recent_approvals"] = len(recent_approvals)
        pd_["innovative_approvals"] = sum(1 for a in recent_approvals if a.is_innovative_drug)
        pd_["pending_review_count"] = sum(
            1 for a in approvals
            if a.review_status and "审评" in (a.review_status or "")
        )

        # ── 临床风险 ──
        failures = [t for t in trials if t.event_type and ("中止" in t.event_type or "失败" in t.event_type)]
        phase3_failures = [f for f in failures if f.trial_phase and "III" in (f.trial_phase or "")]
        active = [t for t in trials if t.event_type and "启动" in t.event_type]
        phase3_active = [t for t in trials if t.trial_phase and "III" in (t.trial_phase or "")]
        pd_["trial_failures"] = len(failures)
        pd_["phase3_failures"] = len(phase3_failures)
        pd_["active_trials"] = len(active)
        pd_["pipeline_phase3"] = len({t.drug_name for t in phase3_active if t.drug_name})

        # ── 医保管控风险 ──
        if procurements:
            cuts = [
                abs(float(p.price_change_ratio))
                for p in procurements
                if p.price_change_ratio is not None
            ]
            pd_["avg_price_cut_ratio"] = sum(cuts) / len(cuts) / 100 if cuts else None
            pd_["procurement_failures"] = sum(
                1 for p in procurements
                if p.bid_result and ("落标" in p.bid_result or "未中" in p.bid_result)
            )
            pd_["procurement_wins"] = sum(
                1 for p in procurements
                if p.bid_result and ("中标" in p.bid_result or "入围" in p.bid_result)
            )

        # ── 合规风险 ──
        pd_["regulatory_total"] = len(reg_risks)
        pd_["regulatory_high_risk"] = sum(
            1 for r in reg_risks if (r.risk_level or "").lower() in ("high", "高")
        )

        # ── 舆情风险 ──
        if news_maps:
            directions = [
                (m.impact_direction or "").lower()
                for m, _ in news_maps
                if m.impact_direction
            ]
            if directions:
                neg = sum(1 for d in directions if d in ("negative", "risk", "down", "负面"))
                pos = sum(1 for d in directions if d in ("positive", "opportunity", "up", "正面"))
                total = len(directions)
                pd_["negative_news_ratio"] = neg / total
                # 情感得分：正面占比*2-1，映射到[-1,1]
                pd_["sentiment_score"] = (pos - neg) / total
                high_neg = sum(
                    1 for m, _ in news_maps
                    if (m.impact_direction or "").lower() in ("negative", "risk", "down", "负面")
                    and _to_float(m.impact_strength) is not None
                    and (_to_float(m.impact_strength) or 0) >= 0.7
                )
                pd_["high_impact_negative"] = high_neg

        return {k: v for k, v in pd_.items() if v is not None}

    # ── 工具方法 ────────────────────────────────────────────────────────────

    def _pick_year(self, rows: list[Any], year: int) -> Any | None:
        """从报表列表中选取目标年份（fiscal_year 或 report_date.year）最新的一条。"""
        candidates = []
        for row in rows:
            fy = getattr(row, "fiscal_year", None)
            if fy is None:
                rd = getattr(row, "report_date", None)
                fy = rd.year if rd else None
            if fy == year:
                candidates.append(row)
        if candidates:
            return candidates[0]
        # 找不到目标年份时，退而求其次取最近一条
        return rows[0] if rows else None

    def _build_metric_map(self, metrics: list[Any], year: int) -> dict[str, float]:
        """将 FinancialMetricHot 列表转为 {metric_name: value} 字典（目标年份优先）。"""
        result: dict[str, float] = {}
        for row in metrics:
            fy = getattr(row, "fiscal_year", None)
            if fy is None:
                rd = getattr(row, "report_date", None)
                fy = rd.year if rd else None
            name = row.metric_name
            if name not in result:
                result[name] = _to_float(row.metric_value)
            elif fy == year:
                result[name] = _to_float(row.metric_value)
        return {k: v for k, v in result.items() if v is not None}

    def _build_suggestion(self, score: PharmaScoreResult, warnings: list[str]) -> str:
        parts: list[str] = []

        if score.total_score >= 70:
            parts.append(f"{score.stock_name}综合评分{score.total_score:.0f}分（{score.level}），基本面较扎实")
        elif score.total_score >= 50:
            parts.append(f"{score.stock_name}综合评分{score.total_score:.0f}分（{score.level}），存在改善空间")
        else:
            parts.append(f"{score.stock_name}综合评分{score.total_score:.0f}分（{score.level}），需重点关注风险")

        if score.strengths:
            parts.append(f"优势维度：{'、'.join(score.strengths[:2])}")
        if score.weaknesses:
            parts.append(f"待改善：{'、'.join(score.weaknesses[:2])}")
        if warnings:
            parts.append(f"注意：{'；'.join(warnings[:2])}")

        return "。".join(parts) + "。"


def to_analysis_summary(result: MedicalAnalysisResult) -> dict[str, Any]:
    """将 MedicalAnalysisResult 转换为 glm_agent._build_analysis_summary() 兼容的格式。

    A 侧接入示例：
        medical = MedicalAnalyzer()
        with container.ctx.session() as db:
            med_result = medical.analyze(db, stock_code, stock_name, year, query)
        analysis_summary = to_analysis_summary(med_result)
        # 直接传入 build_chat_messages(analysis_summary=analysis_summary, ...)
    """
    return {
        "stock_code": result.stock_code,
        "stock_name": result.stock_name,
        "year": result.year,
        "total_score": result.total_score,
        "level": result.level,
        "strengths": result.strengths[:3],
        "weaknesses": result.weaknesses[:3],
        "suggestion": result.suggestion,
        "dimensions": result.dimensions[:4],
        "warnings": result.warnings[:5],
        "data_missing": result.data_missing,
    }


def to_chart_context(result: MedicalAnalysisResult) -> list[dict[str, Any]]:
    """将 MedicalAnalysisResult 转换为 glm_agent._build_chart_context() 兼容的格式。

    A 侧接入示例：
        chart_context = to_chart_context(med_result)
        # 直接传入 build_chat_messages(chart_context=chart_context, ...)
    """
    items = []
    for c in result.charts:
        item: dict[str, Any] = {
            "chart_type": c["chart_type"],
            "title": c["title"],
        }
        if c.get("x_axis"):
            item["x_axis"] = c["x_axis"]
        if c.get("series"):
            item["series"] = c["series"]
        if c.get("extra"):
            item["extra"] = c["extra"]
        items.append(item)
    return items


__all__ = ["MedicalAnalyzer", "MedicalAnalysisResult", "to_analysis_summary", "to_chart_context"]
