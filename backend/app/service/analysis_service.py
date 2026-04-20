"""
企业运营评估模块
多维度打分：盈利能力、偿债能力、研发能力、成长性
基于行业均值归一化，输出 0-100 分 + 文字诊断
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.data.retriever import COMPANY_MAP, METRIC_ALIAS
from db.repository.financial_repo import FinancialDataRepository

PHARMA_BENCHMARKS = {
    "毛利率": {"poor": 30, "avg": 55, "good": 75, "unit": "%", "higher_better": True},
    "净利率": {"poor": 5, "avg": 15, "good": 25, "unit": "%", "higher_better": True},
    "ROE": {"poor": 5, "avg": 12, "good": 20, "unit": "%", "higher_better": True},
    "营业总收入": {"poor": 10, "avg": 80, "good": 200, "unit": "亿元", "higher_better": True},
    "净利润": {"poor": 2, "avg": 15, "good": 50, "unit": "亿元", "higher_better": True},
    "资产负债率": {"poor": 60, "avg": 40, "good": 25, "unit": "%", "higher_better": False},
    "流动比率": {"poor": 1, "avg": 2, "good": 3, "unit": "", "higher_better": True},
    "速动比率": {"poor": 0.8, "avg": 1.5, "good": 2.5, "unit": "", "higher_better": True},
    "每股收益": {"poor": 0.1, "avg": 0.5, "good": 1.5, "unit": "元", "higher_better": True},
}

DIMENSIONS = {
    "盈利能力": ["毛利率", "净利率", "ROE"],
    "偿债能力": ["资产负债率", "流动比率", "速动比率"],
    "成长性": ["营业总收入", "净利润"],
    "每股价值": ["每股收益"],
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


def _normalize(value: float, benchmark: dict) -> float:
    poor = benchmark["poor"]
    avg = benchmark["avg"]
    good = benchmark["good"]
    higher = benchmark["higher_better"]

    if higher:
        if value >= good:
            return 90 + min(10, (value - good) / (good - avg + 1) * 10)
        if value >= avg:
            return 60 + (value - avg) / (good - avg) * 30
        if value >= poor:
            return 30 + (value - poor) / (avg - poor) * 30
        return max(0, 30 * value / poor)

    if value <= good:
        return 90 + min(10, (good - value) / (good + 1) * 10)
    if value <= avg:
        return 60 + (avg - value) / (avg - good) * 30
    if value <= poor:
        return 30 + (poor - value) / (poor - avg) * 30
    return max(0, 30 * (2 * poor - value) / poor)


def _score_to_level(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 65:
        return "良好"
    if score >= 45:
        return "一般"
    return "较差"


class AnalysisService:
    def __init__(self) -> None:
        self.repo = FinancialDataRepository()

    def get_metric_snapshot(
        self,
        db: Session,
        stock_code: str,
        year: int,
        metric_name: str,
    ) -> dict | None:
        normalized_stock_code = self._normalize_stock_code(stock_code)
        std_metric = METRIC_ALIAS.get(metric_name, metric_name)
        row = self.repo.get_metric(db, normalized_stock_code, year, std_metric)
        if row is None:
            return None
        return {
            "stock_code": row.stock_code,
            "stock_name": row.stock_name,
            "year": row.year,
            "metric_name": row.metric_name,
            "metric_value": float(row.metric_value) if row.metric_value is not None else None,
            "metric_unit": row.metric_unit,
            "source": row.source,
        }

    def compare_metric(
        self,
        db: Session,
        metric_name: str,
        year: int,
        stock_codes: list[str] | None = None,
    ) -> dict:
        normalized_codes = [self._normalize_stock_code(code) for code in stock_codes] if stock_codes else None
        std_metric = METRIC_ALIAS.get(metric_name, metric_name)
        rows = self.repo.compare_metric(db, std_metric, year, normalized_codes)
        return {
            "metric": std_metric,
            "year": year,
            "data": [
                {
                    "stock_code": row.stock_code,
                    "stock_name": row.stock_name,
                    "value": float(row.metric_value) if row.metric_value is not None else None,
                    "unit": row.metric_unit,
                }
                for row in rows
            ],
        }

    def get_metric_trend(self, db: Session, symbol: str, metric_name: str) -> dict:
        normalized_stock_code = self._normalize_stock_code(symbol)
        std_metric = METRIC_ALIAS.get(metric_name, metric_name)
        years = self.repo.get_company_years(db, normalized_stock_code)

        trend = []
        for year in sorted(years):
            row = self.repo.get_metric(db, normalized_stock_code, year, std_metric)
            if row:
                trend.append(
                    {
                        "year": year,
                        "value": float(row.metric_value) if row.metric_value is not None else None,
                        "unit": row.metric_unit,
                    }
                )

        stock_name = self.repo.get_by_company_year(db, normalized_stock_code, years[0])[0].stock_name if years else normalized_stock_code
        return {
            "stock_code": normalized_stock_code,
            "stock_name": stock_name,
            "metric": std_metric,
            "trend": trend,
        }

    def diagnose(self, db: Session, stock_code: str, year: int = 2024) -> DiagnoseResult | None:
        normalized_stock_code = self._normalize_stock_code(stock_code)
        rows = self.repo.get_by_company_year(db, normalized_stock_code, year)
        if not rows:
            years = self.repo.get_company_years(db, normalized_stock_code)
            if not years:
                return None
            year = years[0]
            rows = self.repo.get_by_company_year(db, normalized_stock_code, year)

        stock_name = rows[0].stock_name
        data = {row.metric_name: float(row.metric_value) for row in rows if row.metric_value is not None}

        dimension_scores: list[DimensionScore] = []
        all_scores: list[float] = []
        for dim_name, metrics in DIMENSIONS.items():
            metric_details = {}
            scores = []
            for metric in metrics:
                if metric not in data or metric not in PHARMA_BENCHMARKS:
                    continue
                value = data[metric]
                benchmark = PHARMA_BENCHMARKS[metric]
                score = _normalize(value, benchmark)
                scores.append(score)
                metric_details[metric] = (value, benchmark["unit"], round(score, 1))

            if not scores:
                continue

            dim_score = round(sum(scores) / len(scores), 1)
            all_scores.append(dim_score)
            level = _score_to_level(dim_score)
            dimension_scores.append(
                DimensionScore(
                    name=dim_name,
                    score=dim_score,
                    metrics=metric_details,
                    comment=f"{dim_name}处于{level}水平（{dim_score:.0f}分）",
                )
            )

        if "净利率" in data:
            rd_proxy = data["净利率"]
            rd_score = _normalize(
                rd_proxy,
                {"poor": 5, "avg": 15, "good": 25, "unit": "%", "higher_better": True},
            )
            all_scores.append(rd_score)
            dimension_scores.append(
                DimensionScore(
                    name="研发/盈利综合",
                    score=round(rd_score, 1),
                    metrics={"净利率": (rd_proxy, "%", round(rd_score, 1))},
                    comment=f"研发/盈利综合处于{_score_to_level(rd_score)}水平（{rd_score:.0f}分）",
                )
            )

        total = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        level = _score_to_level(total)

        strengths: list[str] = []
        weaknesses: list[str] = []
        for dim in dimension_scores:
            if dim.score >= 70:
                strengths.append(f"{dim.name}（{dim.score:.0f}分）")
            elif dim.score < 45:
                weaknesses.append(f"{dim.name}（{dim.score:.0f}分）")

        suggestion_parts = []
        if weaknesses:
            suggestion_parts.append(f"重点关注{'/'.join(weaknesses)}方面的改善")
        if "资产负债率" in data and data["资产负债率"] > 50:
            suggestion_parts.append("负债率偏高，注意控制财务杠杆")
        if "毛利率" in data and data["毛利率"] > 70:
            suggestion_parts.append("毛利率优秀，具备较强定价能力")
        suggestion = "；".join(suggestion_parts) if suggestion_parts else "整体运营稳健，持续关注行业政策变化"

        return DiagnoseResult(
            stock_code=normalized_stock_code,
            stock_name=stock_name,
            year=year,
            total_score=total,
            level=level,
            dimensions=dimension_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestion=suggestion,
        )

    def scan_risks(self, db: Session, stock_codes: list[str] | None = None) -> list[dict]:
        if stock_codes is None:
            stock_codes = ["600276", "603259", "300015"]

        results = []
        for raw_code in stock_codes:
            code = self._normalize_stock_code(raw_code)
            years_data: dict[int, dict] = {}
            for year in [2022, 2023, 2024]:
                rows = self.repo.get_by_company_year(db, code, year)
                if rows:
                    years_data[year] = {
                        row.metric_name: float(row.metric_value)
                        for row in rows
                        if row.metric_value is not None
                    }

            if not years_data:
                continue

            stock_name = self.repo.get_by_company_year(db, code, max(years_data))[0].stock_name
            risks = []
            opportunities = []

            debt_ratios = [(year, data.get("资产负债率")) for year, data in sorted(years_data.items()) if "资产负债率" in data]
            if len(debt_ratios) >= 2:
                values = [value for _, value in debt_ratios]
                if all(values[i] < values[i + 1] for i in range(len(values) - 1)):
                    latest = values[-1]
                    level = "red" if latest > 50 else "yellow"
                    risks.append(
                        {
                            "signal": "资产负债率连续上升",
                            "detail": f"{debt_ratios[-1][0]}年达{latest:.1f}%",
                            "level": level,
                        }
                    )

            gross_margins = [(year, data.get("毛利率")) for year, data in sorted(years_data.items()) if "毛利率" in data]
            if len(gross_margins) >= 2:
                values = [value for _, value in gross_margins]
                if all(values[i] > values[i + 1] for i in range(len(values) - 1)):
                    drop = values[0] - values[-1]
                    level = "red" if drop > 5 else "yellow"
                    risks.append(
                        {
                            "signal": "毛利率连续下滑",
                            "detail": f"近{len(values)}年累计下滑{drop:.1f}pct",
                            "level": level,
                        }
                    )

            profits = {year: data.get("净利润") for year, data in years_data.items() if "净利润" in data}
            for year in [2023, 2024]:
                if year in profits and (year - 1) in profits and profits[year - 1]:
                    change_pct = (profits[year] - profits[year - 1]) / profits[year - 1] * 100
                    if change_pct < -15:
                        risks.append(
                            {
                                "signal": f"{year}年净利润大幅下滑",
                                "detail": f"同比{change_pct:.1f}%",
                                "level": "red",
                            }
                        )
                    elif change_pct < 0:
                        risks.append(
                            {
                                "signal": f"{year}年净利润小幅下滑",
                                "detail": f"同比{change_pct:.1f}%",
                                "level": "yellow",
                            }
                        )

            revenues = {year: data.get("营业总收入") for year, data in years_data.items() if "营业总收入" in data}
            for year in [2023, 2024]:
                if year in revenues and (year - 1) in revenues and revenues[year - 1]:
                    change_pct = (revenues[year] - revenues[year - 1]) / revenues[year - 1] * 100
                    if change_pct > 15:
                        opportunities.append(
                            {
                                "signal": f"{year}年营收高速增长",
                                "detail": f"同比+{change_pct:.1f}%",
                                "level": "green",
                            }
                        )

            if years_data.get(2024, {}).get("毛利率", 0) > 70:
                opportunities.append(
                    {
                        "signal": "高毛利率，定价能力强",
                        "detail": f"{years_data[2024]['毛利率']:.1f}%",
                        "level": "green",
                    }
                )

            results.append(
                {
                    "stock_code": code,
                    "stock_name": stock_name,
                    "risks": risks,
                    "opportunities": opportunities,
                    "risk_level": "red" if any(risk["level"] == "red" for risk in risks) else "yellow" if risks else "green",
                }
            )

        return results

    def _normalize_stock_code(self, stock_code: str) -> str:
        return COMPANY_MAP.get(stock_code, stock_code) if not stock_code.isdigit() else stock_code


analysis_service = AnalysisService()


def diagnose(db: Session, stock_code: str, year: int = 2024) -> DiagnoseResult | None:
    return analysis_service.diagnose(db, stock_code, year)


def scan_risks(db: Session, stock_codes: list[str] | None = None) -> list[dict]:
    return analysis_service.scan_risks(db, stock_codes)
