import re

from app.data.akshare_client import StockDataProvider
from app.data.pdf_parser import extract_financial_highlights
from app.data.web_scraper import fetch_pharma_news
from app.service.analysis_service import AnalysisService
from app.service.company_service import CompanyService


class AgentTools:
    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.company_service = CompanyService()
        self.analysis_service = AnalysisService()

    def extract_symbol(self, message: str) -> str | None:
        code_match = re.search(r"\b(\d{6})\b", message)
        if code_match:
            return code_match.group(1)
        return self.provider.resolve_symbol(message)

    def get_quote(self, symbol: str) -> dict:
        return self.provider.get_quote(symbol)

    def get_company_dataset(self, db, symbol: str, refresh: bool = False, compact: bool = True) -> dict | None:
        if db is None:
            return None
        return self.company_service.get_company_dataset(db, symbol, refresh=refresh, compact=compact)

    def get_company_context(self, db, symbol: str) -> str:
        if db is None:
            return ""
        return self.company_service.build_company_agent_context(db, symbol)

    def get_pharma_news(self, symbol: str | None = None) -> list[dict]:
        try:
            return fetch_pharma_news(symbol)
        except Exception as exc:
            return [{"error": str(exc), "source": "资讯抓取"}]

    def analyze_financial_data(self, text: str) -> dict:
        try:
            return extract_financial_highlights(text)
        except Exception as exc:
            return {"error": str(exc)}

    def query_financial_metric(self, db, stock_code: str, year: int, metric_name: str) -> str:
        metric = self.analysis_service.get_metric_snapshot(db, stock_code, year, metric_name)
        if metric is None:
            return f"未找到 {stock_code} {year}年 {metric_name} 的数据"
        return (
            f"{metric['stock_name']}（{metric['stock_code']}）{metric['year']}年 {metric['metric_name']}："
            f"{metric['metric_value']}{metric['metric_unit'] or ''}（来源：{metric['source'] or '年报'}）"
        )

    def compare_companies(
        self,
        db,
        metric_name: str,
        year: int = 2024,
        stock_codes: list[str] | None = None,
    ) -> str:
        result = self.analysis_service.compare_metric(db, metric_name, year, stock_codes)
        rows = result["data"]
        if not rows:
            return f"未找到 {year}年 {metric_name} 的对比数据"

        lines = [f"{result['year']}年 {result['metric']} 对比（从高到低）："]
        for index, row in enumerate(rows, 1):
            lines.append(
                f"  {index}. {row['stock_name']}（{row['stock_code']}）：{row['value']}{row['unit'] or ''}"
            )
        return "\n".join(lines)

    def calculate_risk_score(self, db, stock_code: str, year: int = 2024) -> str:
        diagnose_result = self.analysis_service.diagnose(db, stock_code, year)
        if diagnose_result is None:
            risk_list = self.analysis_service.scan_risks(db, [stock_code])
            if not risk_list:
                return f"未找到 {stock_code} 的财务数据"

        risk_list = self.analysis_service.scan_risks(db, [stock_code])
        risk_info = risk_list[0] if risk_list else {"risks": []}
        score = max(0, int(round(diagnose_result.total_score))) if diagnose_result else 0
        level = "低风险" if score >= 80 else "中等风险" if score >= 60 else "高风险"
        stock_name = diagnose_result.stock_name if diagnose_result else stock_code
        stock_code_value = diagnose_result.stock_code if diagnose_result else stock_code
        year_value = diagnose_result.year if diagnose_result else year

        lines = [f"{stock_name}（{stock_code_value}）{year_value}年风险评分：{score}分（{level}）"]
        if risk_info.get("risks"):
            lines.append("风险信号：")
            lines.extend(f"  {item['signal']}，{item['detail']}" for item in risk_info["risks"])
        else:
            lines.append("  未发现明显风险信号，财务状况健康")
        return "\n".join(lines)

    def diagnose_company(self, db, stock_code: str, year: int = 2024) -> str:
        result = self.analysis_service.diagnose(db, stock_code, year)
        if result is None:
            return f"未找到 {stock_code} 的财务数据，无法诊断"

        lines = [
            f"【{result.stock_name}（{result.stock_code}）{result.year}年运营诊断】",
            f"综合评分：{result.total_score:.0f}分（{result.level}）",
            "",
            "各维度得分：",
        ]
        for dim in result.dimensions:
            bar = "█" * int(dim.score / 10) + "░" * (10 - int(dim.score / 10))
            lines.append(f"  {dim.name:<8} {bar} {dim.score:.0f}分")

        if result.strengths:
            lines.append(f"\n优势：{', '.join(result.strengths)}")
        if result.weaknesses:
            lines.append(f"劣势：{', '.join(result.weaknesses)}")
        lines.append(f"\n建议：{result.suggestion}")
        return "\n".join(lines)

    def generate_report(self, db, stock_code: str, user_type: str = "投资者") -> str:
        diag = self.analysis_service.diagnose(db, stock_code)
        risks = self.analysis_service.scan_risks(db, [stock_code])
        risk_info = risks[0] if risks else {}

        if user_type == "投资者":
            focus = "财务健康度、估值、成长潜力、风险提示"
        elif user_type == "管理者":
            focus = "运营效率、行业对标、改进建议"
        else:
            focus = "合规指标、异常波动、信息披露完整性"

        lines = [
            f"[报告生成指令] 请为{user_type}生成{diag.stock_name if diag else stock_code}分析报告",
            f"关注重点：{focus}",
            "",
        ]
        if diag:
            lines += [
                f"综合评分：{diag.total_score:.0f}分（{diag.level}）",
                f"优势：{', '.join(diag.strengths) or '暂无'}",
                f"劣势：{', '.join(diag.weaknesses) or '暂无'}",
                f"建议：{diag.suggestion}",
            ]
        if risk_info.get("risks"):
            lines.append("风险信号：" + "；".join(item["signal"] + item["detail"] for item in risk_info["risks"]))
        if risk_info.get("opportunities"):
            lines.append("机会信号：" + "；".join(item["signal"] + item["detail"] for item in risk_info["opportunities"]))
        return "\n".join(lines)
