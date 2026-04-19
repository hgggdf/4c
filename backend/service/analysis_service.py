"""
企业运营评估模块
多维度打分：盈利能力、偿债能力、研发能力、成长性
基于行业均值归一化，输出 0-100 分 + 文字诊断
"""
from __future__ import annotations

from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from repository.financial_repo import FinancialDataRepository

# 医药行业基准值（行业均值/优秀线）
PHARMA_BENCHMARKS = {
    "毛利率":       {"poor": 30, "avg": 55, "good": 75, "unit": "%",  "higher_better": True},
    "净利率":       {"poor": 5,  "avg": 15, "good": 25, "unit": "%",  "higher_better": True},
    "ROE":          {"poor": 5,  "avg": 12, "good": 20, "unit": "%",  "higher_better": True},
    "营业总收入":   {"poor": 10, "avg": 80, "good": 200,"unit": "亿元","higher_better": True},
    "净利润":       {"poor": 2,  "avg": 15, "good": 50, "unit": "亿元","higher_better": True},
    "资产负债率":   {"poor": 60, "avg": 40, "good": 25, "unit": "%",  "higher_better": False},
    "流动比率":     {"poor": 1,  "avg": 2,  "good": 3,  "unit": "",   "higher_better": True},
    "速动比率":     {"poor": 0.8,"avg": 1.5,"good": 2.5,"unit": "",   "higher_better": True},
    "每股收益":     {"poor": 0.1,"avg": 0.5,"good": 1.5,"unit": "元", "higher_better": True},
}

# 四大维度及其包含的指标
DIMENSIONS = {
    "盈利能力": ["毛利率", "净利率", "ROE"],
    "偿债能力": ["资产负债率", "流动比率", "速动比率"],
    "成长性":   ["营业总收入", "净利润"],
    "每股价值": ["每股收益"],
}

# 研发能力单独处理（数据来源不同）
PHARMA_RD_BENCHMARKS = {
    "poor": 5, "avg": 10, "good": 18, "unit": "%"
}


@dataclass
class DimensionScore:
    name: str
    score: float          # 0-100
    metrics: dict         # {指标名: (值, 单位, 得分)}
    comment: str = ""


@dataclass
class DiagnoseResult:
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str            # 优秀/良好/一般/较差
    dimensions: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestion: str = ""


def _normalize(value: float, benchmark: dict) -> float:
    """把指标值归一化到 0-100 分"""
    poor = benchmark["poor"]
    avg  = benchmark["avg"]
    good = benchmark["good"]
    higher = benchmark["higher_better"]

    if higher:
        if value >= good:
            return 90 + min(10, (value - good) / (good - avg + 1) * 10)
        elif value >= avg:
            return 60 + (value - avg) / (good - avg) * 30
        elif value >= poor:
            return 30 + (value - poor) / (avg - poor) * 30
        else:
            return max(0, 30 * value / poor)
    else:
        # 越低越好（如资产负债率）
        if value <= good:
            return 90 + min(10, (good - value) / (good + 1) * 10)
        elif value <= avg:
            return 60 + (avg - value) / (avg - good) * 30
        elif value <= poor:
            return 30 + (poor - value) / (poor - avg) * 30
        else:
            return max(0, 30 * (2 * poor - value) / poor)


def _score_to_level(score: float) -> str:
    if score >= 80:
        return "优秀"
    elif score >= 65:
        return "良好"
    elif score >= 45:
        return "一般"
    else:
        return "较差"


def diagnose(db: Session, stock_code: str, year: int = 2024) -> DiagnoseResult | None:
    """对单家公司进行多维度运营评估"""
    repo = FinancialDataRepository()
    rows = repo.get_by_company_year(db, stock_code, year)
    if not rows:
        # 尝试最近一年
        years = repo.get_company_years(db, stock_code)
        if not years:
            return None
        year = years[0]
        rows = repo.get_by_company_year(db, stock_code, year)

    stock_name = rows[0].stock_name
    data = {r.metric_name: float(r.metric_value) for r in rows if r.metric_value is not None}

    dimension_scores: list[DimensionScore] = []
    all_scores: list[float] = []

    for dim_name, metrics in DIMENSIONS.items():
        metric_details = {}
        scores = []
        for m in metrics:
            if m not in data or m not in PHARMA_BENCHMARKS:
                continue
            val = data[m]
            bm  = PHARMA_BENCHMARKS[m]
            s   = _normalize(val, bm)
            scores.append(s)
            metric_details[m] = (val, bm["unit"], round(s, 1))

        if not scores:
            continue

        dim_score = round(sum(scores) / len(scores), 1)
        all_scores.append(dim_score)

        # 维度文字评价
        level = _score_to_level(dim_score)
        comment = f"{dim_name}处于{level}水平（{dim_score:.0f}分）"
        dimension_scores.append(DimensionScore(
            name=dim_name, score=dim_score,
            metrics=metric_details, comment=comment
        ))

    # 研发能力维度（用净利率近似，实际研发费用率数据暂缺）
    if "净利率" in data:
        rd_proxy = data["净利率"]
        rd_score = _normalize(rd_proxy, {"poor": 5, "avg": 15, "good": 25,
                                          "unit": "%", "higher_better": True})
        all_scores.append(rd_score)
        dimension_scores.append(DimensionScore(
            name="研发/盈利综合",
            score=round(rd_score, 1),
            metrics={"净利率": (rd_proxy, "%", round(rd_score, 1))},
            comment=f"研发/盈利综合处于{_score_to_level(rd_score)}水平（{rd_score:.0f}分）"
        ))

    total = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    level = _score_to_level(total)

    # 优势与劣势
    strengths, weaknesses = [], []
    for dim in dimension_scores:
        if dim.score >= 70:
            strengths.append(f"{dim.name}（{dim.score:.0f}分）")
        elif dim.score < 45:
            weaknesses.append(f"{dim.name}（{dim.score:.0f}分）")

    # 建议
    suggestion_parts = []
    if weaknesses:
        suggestion_parts.append(f"重点关注{'/'.join(weaknesses)}方面的改善")
    if "资产负债率" in data and data["资产负债率"] > 50:
        suggestion_parts.append("负债率偏高，注意控制财务杠杆")
    if "毛利率" in data and data["毛利率"] > 70:
        suggestion_parts.append("毛利率优秀，具备较强定价能力")
    suggestion = "；".join(suggestion_parts) if suggestion_parts else "整体运营稳健，持续关注行业政策变化"

    return DiagnoseResult(
        stock_code=stock_code,
        stock_name=stock_name,
        year=year,
        total_score=total,
        level=level,
        dimensions=dimension_scores,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestion=suggestion,
    )


def scan_risks(db: Session, stock_codes: list[str] | None = None) -> list[dict]:
    """
    扫描风险信号：
    - 资产负债率连续上升
    - 毛利率连续下滑
    - 净利润同比下降超过 15%
    返回风险列表，每条含 level(red/yellow/green)
    """
    repo = FinancialDataRepository()
    if stock_codes is None:
        stock_codes = ["600276", "603259", "300015"]

    results = []

    for code in stock_codes:
        years_data: dict[int, dict] = {}
        for year in [2022, 2023, 2024]:
            rows = repo.get_by_company_year(db, code, year)
            if rows:
                years_data[year] = {r.metric_name: float(r.metric_value)
                                    for r in rows if r.metric_value is not None}

        if not years_data:
            continue

        stock_name = repo.get_by_company_year(db, code, max(years_data))[0].stock_name
        risks = []
        opportunities = []

        # 资产负债率连续上升
        debt_ratios = [(y, d.get("资产负债率")) for y, d in sorted(years_data.items()) if "资产负债率" in d]
        if len(debt_ratios) >= 2:
            vals = [v for _, v in debt_ratios]
            if all(vals[i] < vals[i+1] for i in range(len(vals)-1)):
                latest = vals[-1]
                level = "red" if latest > 50 else "yellow"
                risks.append({"signal": "资产负债率连续上升",
                               "detail": f"{debt_ratios[-1][0]}年达{latest:.1f}%",
                               "level": level})

        # 毛利率连续下滑
        gross_margins = [(y, d.get("毛利率")) for y, d in sorted(years_data.items()) if "毛利率" in d]
        if len(gross_margins) >= 2:
            vals = [v for _, v in gross_margins]
            if all(vals[i] > vals[i+1] for i in range(len(vals)-1)):
                drop = vals[0] - vals[-1]
                level = "red" if drop > 5 else "yellow"
                risks.append({"signal": "毛利率连续下滑",
                               "detail": f"近{len(vals)}年累计下滑{drop:.1f}pct",
                               "level": level})

        # 净利润同比下降超15%
        profits = {y: d.get("净利润") for y, d in years_data.items() if "净利润" in d}
        for y in [2023, 2024]:
            if y in profits and (y-1) in profits and profits[y-1]:
                chg = (profits[y] - profits[y-1]) / profits[y-1] * 100
                if chg < -15:
                    risks.append({"signal": f"{y}年净利润大幅下滑",
                                   "detail": f"同比{chg:.1f}%",
                                   "level": "red"})
                elif chg < 0:
                    risks.append({"signal": f"{y}年净利润小幅下滑",
                                   "detail": f"同比{chg:.1f}%",
                                   "level": "yellow"})

        # 机会信号：营收逆势增长
        revenues = {y: d.get("营业总收入") for y, d in years_data.items() if "营业总收入" in d}
        for y in [2023, 2024]:
            if y in revenues and (y-1) in revenues and revenues[y-1]:
                chg = (revenues[y] - revenues[y-1]) / revenues[y-1] * 100
                if chg > 15:
                    opportunities.append({"signal": f"{y}年营收高速增长",
                                           "detail": f"同比+{chg:.1f}%",
                                           "level": "green"})

        # 高毛利率机会
        if years_data.get(2024, {}).get("毛利率", 0) > 70:
            opportunities.append({"signal": "高毛利率，定价能力强",
                                   "detail": f"{years_data[2024]['毛利率']:.1f}%",
                                   "level": "green"})

        results.append({
            "stock_code": code,
            "stock_name": stock_name,
            "risks": risks,
            "opportunities": opportunities,
            "risk_level": "red" if any(r["level"] == "red" for r in risks)
                          else "yellow" if risks else "green",
        })

    return results
