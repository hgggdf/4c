"""企业运营分析服务。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.company import CompanyMaster
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.news_hot import NewsHot

from .shared import normalize_percent, resolve_company, to_float

METRIC_ALIASES = {
    "营收": "营业总收入",
    "营业收入": "营业总收入",
    "营业总收入": "营业总收入",
    "净利润": "净利润",
    "毛利率": "毛利率",
    "ROE": "ROE",
    "净资产收益率": "ROE",
    "资产负债率": "资产负债率",
    "研发费用率": "研发费用率",
    "研发投入占比": "研发费用率",
    "每股收益": "每股收益",
    "基本每股收益": "每股收益",
    "经营现金流量净额": "经营现金流量净额",
    "净利率": "净利率",
    "营业总收入增长率": "营业总收入增长率",
    "净利润增长率": "净利润增长率",
}

METRIC_RULES = {
    "毛利率": {"poor": 20, "avg": 45, "good": 65, "unit": "%", "higher_better": True},
    "净利率": {"poor": 5, "avg": 12, "good": 22, "unit": "%", "higher_better": True},
    "ROE": {"poor": 5, "avg": 12, "good": 20, "unit": "%", "higher_better": True},
    "资产负债率": {"poor": 65, "avg": 45, "good": 25, "unit": "%", "higher_better": False},
    "研发费用率": {"poor": 3, "avg": 8, "good": 15, "unit": "%", "higher_better": True},
    "营业总收入增长率": {"poor": 0, "avg": 10, "good": 25, "unit": "%", "higher_better": True},
    "净利润增长率": {"poor": 0, "avg": 10, "good": 25, "unit": "%", "higher_better": True},
    "每股收益": {"poor": 0.1, "avg": 0.5, "good": 1.5, "unit": "元", "higher_better": True},
}

DIMENSIONS = {
    "盈利能力": ["毛利率", "净利率", "ROE"],
    "偿债能力": ["资产负债率", "每股收益"],
    "成长性": ["营业总收入增长率", "净利润增长率"],
    "创新投入": ["研发费用率"],
}


@dataclass
class DimensionScore:
    name: str
    score: float
    metrics: dict
    comment: str = ""


@dataclass
class DiagnoseResult:
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class YearSnapshot:
    year: int
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    debt_ratio: float | None = None
    rd_ratio: float | None = None
    operating_cashflow: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None


def _score_metric(value: float, rule: dict) -> float:
    poor = rule["poor"]
    avg = rule["avg"]
    good = rule["good"]
    higher = rule["higher_better"]

    if higher:
        if value >= good:
            return 90 + min(10, (value - good) / (abs(good) + 1) * 10)
        if value >= avg:
            return 60 + (value - avg) / max(good - avg, 1e-6) * 30
        if value >= poor:
            return 30 + (value - poor) / max(avg - poor, 1e-6) * 30
        return max(0, 30 * value / max(poor, 1e-6))

    if value <= good:
        return 90 + min(10, (good - value) / (abs(good) + 1) * 10)
    if value <= avg:
        return 60 + (avg - value) / max(avg - good, 1e-6) * 30
    if value <= poor:
        return 30 + (poor - value) / max(poor - avg, 1e-6) * 30
    return max(0, 30 * (2 * poor - value) / max(poor, 1e-6))


def _score_to_level(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 65:
        return "良好"
    if score >= 45:
        return "一般"
    return "较差"


class AnalysisService:
    """基于当前财务、公告和新闻热表提供分析能力。"""

    def get_metric_snapshot(
        self,
        db: Session,
        stock_code: str,
        year: int,
        metric_name: str,
    ) -> dict | None:
        company = self._require_company(db, stock_code)
        snapshots = self._load_snapshots(db, company.stock_code)
        snapshot = self._select_year_snapshot(snapshots, year)
        if snapshot is None:
            return None

        metric = self._standard_metric_name(metric_name)
        value, unit = self._metric_from_snapshot(snapshot, metric)
        if value is None:
            return None
        return {
            "stock_code": company.stock_code,
            "stock_name": company.stock_name,
            "year": snapshot.year,
            "metric_name": metric,
            "metric_value": value,
            "metric_unit": unit,
            "source": "database_hot_tables",
            "company_profile": {
                "industry_level1": company.industry_level1,
                "industry_level2": company.industry_level2,
                "exchange": company.exchange,
            },
        }

    def compare_metric(
        self,
        db: Session,
        metric_name: str,
        year: int,
        stock_codes: list[str] | None = None,
    ) -> dict:
        metric = self._standard_metric_name(metric_name)
        target_codes = self._resolve_stock_codes(db, stock_codes)
        items = []
        for code in target_codes:
            company = self._require_company(db, code)
            snapshot = self._select_year_snapshot(self._load_snapshots(db, company.stock_code), year)
            if snapshot is None:
                continue
            value, unit = self._metric_from_snapshot(snapshot, metric)
            if value is None:
                continue
            items.append(
                {
                    "stock_code": company.stock_code,
                    "stock_name": company.stock_name,
                    "value": round(value, 4),
                    "unit": unit,
                    "industry_level1": company.industry_level1,
                    "industry_level2": company.industry_level2,
                }
            )

        higher_better = METRIC_RULES.get(metric, {}).get("higher_better", True)
        items.sort(key=lambda item: item["value"], reverse=higher_better)
        return {"metric": metric, "year": year, "data": items}

    def get_metric_trend(self, db: Session, symbol: str, metric_name: str) -> dict:
        company = self._require_company(db, symbol)
        metric = self._standard_metric_name(metric_name)
        snapshots = self._load_snapshots(db, company.stock_code)

        trend = []
        for year in sorted(snapshots):
            value, unit = self._metric_from_snapshot(snapshots[year], metric)
            if value is None:
                continue
            trend.append({"year": year, "value": round(value, 4), "unit": unit})

        return {
            "stock_code": company.stock_code,
            "stock_name": company.stock_name,
            "metric": metric,
            "trend": trend,
        }

    def diagnose(self, db: Session, stock_code: str, year: int = 2024) -> DiagnoseResult | None:
        company = self._require_company(db, stock_code)
        snapshot = self._select_year_snapshot(self._load_snapshots(db, company.stock_code), year)
        if snapshot is None:
            return None

        dimensions: list[DimensionScore] = []
        all_scores: list[float] = []
        for dim_name, metrics in DIMENSIONS.items():
            metric_details = {}
            scores = []
            for metric in metrics:
                value, unit = self._metric_from_snapshot(snapshot, metric)
                rule = METRIC_RULES.get(metric)
                if value is None or rule is None:
                    continue
                score = _score_metric(value, rule)
                scores.append(score)
                metric_details[metric] = {
                    "value": round(value, 4),
                    "unit": unit,
                    "score": round(score, 1),
                }
            if not scores:
                continue

            dim_score = round(sum(scores) / len(scores), 1)
            dimensions.append(
                DimensionScore(
                    name=dim_name,
                    score=dim_score,
                    metrics=metric_details,
                    comment=f"{dim_name}处于{_score_to_level(dim_score)}水平（{dim_score:.0f}分）",
                )
            )
            all_scores.append(dim_score)

        if not dimensions:
            return None

        total_score = round(sum(all_scores) / len(all_scores), 1)
        strengths = [f"{item.name}（{item.score:.0f}分）" for item in dimensions if item.score >= 75]
        weaknesses = [f"{item.name}（{item.score:.0f}分）" for item in dimensions if item.score < 50]

        suggestion_parts = []
        if any(item.name == "偿债能力" and item.score < 60 for item in dimensions):
            suggestion_parts.append("优先优化负债结构和现金回笼效率")
        if any(item.name == "成长性" and item.score < 60 for item in dimensions):
            suggestion_parts.append("重点跟踪营收扩张与利润兑现节奏")
        if any(item.name == "创新投入" and item.score < 60 for item in dimensions):
            suggestion_parts.append("需要继续提升研发投入强度和成果转化效率")
        if not suggestion_parts:
            suggestion_parts.append("整体经营结构相对稳健，建议持续跟踪行业政策与产品落地进度")

        return DiagnoseResult(
            stock_code=company.stock_code,
            stock_name=company.stock_name,
            year=snapshot.year,
            total_score=total_score,
            level=_score_to_level(total_score),
            dimensions=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestion="；".join(suggestion_parts),
        )

    def scan_risks(self, db: Session, stock_codes: list[str] | None = None) -> list[dict]:
        results = []
        for code in self._resolve_stock_codes(db, stock_codes):
            company = self._require_company(db, code)
            snapshots = self._load_snapshots(db, company.stock_code)
            if not snapshots:
                continue
            latest_year = max(snapshots)
            latest = snapshots[latest_year]

            risks: list[dict] = []
            opportunities: list[dict] = []
            self._append_financial_signals(latest, risks, opportunities)
            self._append_announcement_signals(db, company.stock_code, risks, opportunities)
            self._append_news_signals(db, company.stock_code, risks, opportunities)

            risk_level = "green"
            if any(item["level"] == "red" for item in risks):
                risk_level = "red"
            elif risks:
                risk_level = "yellow"

            results.append(
                {
                    "stock_code": company.stock_code,
                    "stock_name": company.stock_name,
                    "risk_level": risk_level,
                    "risks": risks[:8],
                    "opportunities": opportunities[:8],
                }
            )
        return results

    def _require_company(self, db: Session, symbol: str) -> CompanyMaster:
        company = resolve_company(db, symbol)
        if company is None:
            raise ValueError(f"company not found: {symbol}")
        return company

    def _resolve_stock_codes(self, db: Session, stock_codes: list[str] | None) -> list[str]:
        if stock_codes:
            resolved = []
            for item in stock_codes:
                company = resolve_company(db, item)
                if company is not None:
                    resolved.append(company.stock_code)
            if resolved:
                return resolved

        fallback = list(
            db.execute(select(CompanyMaster).order_by(CompanyMaster.stock_code.asc()).limit(3)).scalars().all()
        )
        return [item.stock_code for item in fallback]

    def _load_snapshots(self, db: Session, stock_code: str) -> dict[int, YearSnapshot]:
        all_rows = list(
            db.execute(
                select(FinancialHot)
                .where(FinancialHot.stock_code == stock_code)
                .order_by(FinancialHot.report_date.desc(), FinancialHot.created_at.desc())
            ).scalars().all()
        )

        by_year = self._latest_by_year(all_rows, "fiscal_year")

        snapshots: dict[int, YearSnapshot] = {}
        for year, row in by_year.items():
            snapshots[year] = YearSnapshot(
                year=year,
                revenue=to_float(getattr(row, "revenue", None), None),
                net_profit=to_float(getattr(row, "net_profit", None), None),
                eps=to_float(getattr(row, "eps", None), None),
                gross_margin=normalize_percent(to_float(getattr(row, "gross_margin", None), None))
                    or self._ratio(getattr(row, "gross_profit", None), getattr(row, "revenue", None)),
                net_margin=self._ratio(getattr(row, "net_profit", None), getattr(row, "revenue", None)),
                roe=self._ratio(getattr(row, "net_profit", None), getattr(row, "total_assets", None)),
                debt_ratio=normalize_percent(to_float(getattr(row, "debt_ratio", None), None))
                    or self._ratio(getattr(row, "total_liabilities", None), getattr(row, "total_assets", None)),
                rd_ratio=normalize_percent(to_float(getattr(row, "rd_ratio", None), None))
                    or self._ratio(getattr(row, "rd_expense", None), getattr(row, "revenue", None)),
                operating_cashflow=to_float(getattr(row, "operating_cashflow", None), None),
            )

        ordered_years = sorted(snapshots, reverse=True)
        for index, year in enumerate(ordered_years[:-1]):
            current = snapshots[year]
            previous = snapshots[ordered_years[index + 1]]
            current.revenue_growth = self._growth(current.revenue, previous.revenue)
            current.profit_growth = self._growth(current.net_profit, previous.net_profit)
        return snapshots

    def _latest_by_year(self, rows, year_attr: str) -> dict[int, object]:
        grouped = {}
        for row in rows:
            year = getattr(row, year_attr, None)
            if year is None:
                report_date = getattr(row, "report_date", None)
                year = report_date.year if report_date is not None else None
            if year is None or int(year) in grouped:
                continue
            grouped[int(year)] = row
        return grouped

    def _ratio(self, numerator, denominator) -> float | None:
        num = to_float(numerator, None)
        den = to_float(denominator, None)
        if num is None or den in (None, 0):
            return None
        return round(num / den * 100, 4)

    def _growth(self, current: float | None, previous: float | None) -> float | None:
        if current is None or previous in (None, 0):
            return None
        return round((current - previous) / abs(previous) * 100, 4)

    def _select_year_snapshot(self, snapshots: dict[int, YearSnapshot], year: int) -> YearSnapshot | None:
        if not snapshots:
            return None
        if year in snapshots:
            return snapshots[year]
        smaller_or_equal = [key for key in snapshots if key <= year]
        if smaller_or_equal:
            return snapshots[max(smaller_or_equal)]
        return snapshots[max(snapshots)]

    def _standard_metric_name(self, metric_name: str) -> str:
        return METRIC_ALIASES.get(metric_name, metric_name)

    def _metric_from_snapshot(self, snapshot: YearSnapshot, metric_name: str) -> tuple[float | None, str]:
        mapping = {
            "营业总收入": (snapshot.revenue, ""),
            "净利润": (snapshot.net_profit, ""),
            "毛利率": (snapshot.gross_margin, "%"),
            "ROE": (snapshot.roe, "%"),
            "资产负债率": (snapshot.debt_ratio, "%"),
            "研发费用率": (snapshot.rd_ratio, "%"),
            "每股收益": (snapshot.eps, "元"),
            "经营现金流量净额": (snapshot.operating_cashflow, ""),
            "净利率": (snapshot.net_margin, "%"),
            "营业总收入增长率": (snapshot.revenue_growth, "%"),
            "净利润增长率": (snapshot.profit_growth, "%"),
        }
        return mapping.get(metric_name, (None, ""))

    def _append_financial_signals(self, snapshot: YearSnapshot, risks: list[dict], opportunities: list[dict]) -> None:
        if snapshot.debt_ratio is not None and snapshot.debt_ratio >= 60:
            level = "red" if snapshot.debt_ratio >= 70 else "yellow"
            risks.append({
                "signal": "资产负债率偏高",
                "detail": f"{snapshot.year}年资产负债率为 {snapshot.debt_ratio:.2f}%",
                "level": level,
            })
        if snapshot.gross_margin is not None and snapshot.gross_margin < 25:
            risks.append({
                "signal": "毛利率偏低",
                "detail": f"{snapshot.year}年毛利率为 {snapshot.gross_margin:.2f}%",
                "level": "yellow",
            })
        if snapshot.revenue_growth is not None and snapshot.revenue_growth < -10:
            risks.append({
                "signal": "营收增速转弱",
                "detail": f"{snapshot.year}年营业总收入同比 {snapshot.revenue_growth:.2f}%",
                "level": "red",
            })
        if snapshot.net_profit is not None and snapshot.net_profit <= 0:
            risks.append({
                "signal": "净利润为负",
                "detail": f"{snapshot.year}年净利润为 {snapshot.net_profit:.2f}",
                "level": "red",
            })

        if snapshot.gross_margin is not None and snapshot.gross_margin >= 60:
            opportunities.append({
                "signal": "毛利率表现优秀",
                "detail": f"{snapshot.year}年毛利率达到 {snapshot.gross_margin:.2f}%",
            })
        if snapshot.roe is not None and snapshot.roe >= 15:
            opportunities.append({
                "signal": "股东回报能力较强",
                "detail": f"{snapshot.year}年 ROE 为 {snapshot.roe:.2f}%",
            })
        if snapshot.rd_ratio is not None and snapshot.rd_ratio >= 10:
            opportunities.append({
                "signal": "研发投入强度较高",
                "detail": f"{snapshot.year}年研发费用率为 {snapshot.rd_ratio:.2f}%",
            })
        if snapshot.revenue_growth is not None and snapshot.revenue_growth >= 15:
            opportunities.append({
                "signal": "营收增长势头积极",
                "detail": f"{snapshot.year}年营业总收入同比 {snapshot.revenue_growth:.2f}%",
            })

    def _append_announcement_signals(self, db: Session, stock_code: str, risks: list[dict], opportunities: list[dict]) -> None:
        announcements = list(
            db.execute(
                select(AnnouncementHot)
                .where(AnnouncementHot.stock_code == stock_code)
                .order_by(AnnouncementHot.publish_date.desc(), AnnouncementHot.created_at.desc())
                .limit(5)
            ).scalars().all()
        )
        for row in announcements:
            ann_type = (row.announcement_type or "").lower()
            key_fields = row.key_fields_json or {}
            if isinstance(key_fields, str):
                try:
                    key_fields = json.loads(key_fields)
                except Exception:
                    key_fields = {}
            signal_type = key_fields.get("signal_type", "")
            if signal_type == "risk" or "风险" in ann_type or "处罚" in ann_type:
                risks.append({
                    "signal": f"公告风险信号：{row.announcement_type or '公告'}",
                    "detail": row.summary_text or row.title or "公告提示潜在风险",
                    "level": "yellow",
                })
            elif signal_type == "opportunity" or "审批" in ann_type or "获批" in ann_type or "中标" in ann_type:
                opportunities.append({
                    "signal": f"公告积极信号：{row.announcement_type or '公告'}",
                    "detail": row.summary_text or row.title or "公告提示积极进展",
                })

    def _append_news_signals(self, db: Session, stock_code: str, risks: list[dict], opportunities: list[dict]) -> None:
        all_news = list(
            db.execute(
                select(NewsHot)
                .where(NewsHot.related_stock_codes_json.isnot(None))
                .order_by(NewsHot.publish_time.desc(), NewsHot.created_at.desc())
                .limit(30)
            ).scalars().all()
        )
        matched = []
        for row in all_news:
            codes = row.related_stock_codes_json
            if isinstance(codes, str):
                try:
                    codes = json.loads(codes)
                except Exception:
                    codes = [codes]
            if isinstance(codes, list) and stock_code in codes:
                matched.append(row)
            elif isinstance(codes, dict) and stock_code in codes:
                matched.append(row)
            if len(matched) >= 5:
                break
        for news in matched:
            key_fields = news.key_fields_json or {}
            if isinstance(key_fields, str):
                try:
                    key_fields = json.loads(key_fields)
                except Exception:
                    key_fields = {}
            direction = str(key_fields.get("impact_direction", "")).lower()
            detail = news.summary_text or news.title
            if direction in {"negative", "risk", "down"}:
                risks.append({
                    "signal": "新闻舆情偏负面",
                    "detail": detail,
                    "level": "yellow",
                })
            elif direction in {"positive", "opportunity", "up"}:
                opportunities.append({
                    "signal": "新闻舆情偏正面",
                    "detail": detail,
                })