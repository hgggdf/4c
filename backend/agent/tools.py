import re

from data.company_data_store import CompanyDataStore
from data.akshare_client import StockDataProvider
from data.web_scraper import fetch_pharma_news
from data.pdf_parser import extract_financial_highlights


class AgentTools:
    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.company_store = CompanyDataStore()

    def extract_symbol(self, message: str) -> str | None:
        code_match = re.search(r"\b(\d{6})\b", message)
        if code_match:
            return code_match.group(1)
        return self.provider.resolve_symbol(message)

    def get_quote(self, symbol: str) -> dict:
        return self.provider.get_quote(symbol)

    def get_company_dataset(self, symbol: str, refresh: bool = False, compact: bool = True) -> dict | None:
        dataset = None if refresh else self.company_store.load_company_dataset(symbol, compact=compact)
        if dataset is not None:
            return dataset

        full_dataset = self.provider.collect_company_dataset(symbol)
        self.company_store.save_company_dataset(full_dataset)
        return self.company_store.to_compact_dataset(full_dataset) if compact else full_dataset

    def get_company_context(self, symbol: str) -> str:
        dataset = self.get_company_dataset(symbol, refresh=False, compact=True)
        if not dataset:
            return ""

        parts: list[str] = []
        info = dataset.get("company_info", {})
        if info:
            parts.append(
                f"【公司资料】{dataset.get('name', symbol)}（{symbol}），行业：{info.get('行业', '未知')}，"
                f"总市值：{info.get('总市值', '未知')}，流通市值：{info.get('流通市值', '未知')}，上市时间：{info.get('上市时间', '未知')}"
            )

        reports = dataset.get("research_reports", [])[:3]
        if reports:
            parts.append(
                "【最新研报】\n" + "\n".join(
                    f"- [{item.get('日期', '')}] {item.get('报告名称', '')}（{item.get('机构', '')}，评级 {item.get('东财评级', '')}）"
                    for item in reports
                )
            )

        notices = dataset.get("announcements", [])[:5]
        if notices:
            parts.append(
                "【最新公告】\n" + "\n".join(
                    f"- [{item.get('公告日期', '')}] {item.get('公告标题', '')}（{item.get('公告类型', '')}）"
                    for item in notices
                )
            )

        financial_abstract = dataset.get("financial_abstract", [])
        key_metrics = []
        metric_names = {"归母净利润", "营业总收入", "扣非净利润", "净资产收益率", "毛利率"}
        for row in financial_abstract:
            if row.get("指标") not in metric_names:
                continue
            latest_pairs = [
                (key, value)
                for key, value in row.items()
                if key not in {"选项", "指标"} and value not in (None, "")
            ]
            if latest_pairs:
                latest_key, latest_value = latest_pairs[0]
                key_metrics.append(f"{row.get('指标')}（{latest_key}）：{latest_value}")
            if len(key_metrics) >= 5:
                break
        if key_metrics:
            parts.append("【财务摘要】" + "；".join(key_metrics))

        main_business = dataset.get("main_business", [])[:5]
        if main_business:
            parts.append(
                "【主营构成】\n" + "\n".join(
                    f"- {item.get('分类类型', '')} / {item.get('主营构成', '')}：收入 {item.get('主营收入', '')}，毛利率 {item.get('毛利率', '')}"
                    for item in main_business
                )
            )

        return "\n\n".join(parts)

    def get_pharma_news(self, symbol: str | None = None) -> list[dict]:
        try:
            return fetch_pharma_news(symbol)
        except Exception as e:
            return [{"error": str(e), "source": "资讯抓取"}]

    def analyze_financial_data(self, text: str) -> dict:
        try:
            return extract_financial_highlights(text)
        except Exception as e:
            return {"error": str(e)}

    # ── 新增结构化工具 ────────────────────────────────────────────────────────

    def query_financial_metric(
        self, db, stock_code: str, year: int, metric_name: str
    ) -> str:
        """查询单个财务指标，返回格式化字符串"""
        from repository.financial_repo import FinancialDataRepository
        from data.retriever import METRIC_ALIAS, COMPANY_MAP

        # 支持中文别名
        std_metric = METRIC_ALIAS.get(metric_name, metric_name)
        # 支持公司名转代码
        if not stock_code.isdigit():
            stock_code = COMPANY_MAP.get(stock_code, stock_code)

        repo = FinancialDataRepository()
        row = repo.get_metric(db, stock_code, year, std_metric)
        if row is None:
            return f"未找到 {stock_code} {year}年 {metric_name} 的数据"
        return (
            f"{row.stock_name}（{row.stock_code}）{year}年 {row.metric_name}："
            f"{row.metric_value}{row.metric_unit or ''}（来源：{row.source or '年报'}）"
        )

    def compare_companies(
        self, db, metric_name: str, year: int = 2024,
        stock_codes: list[str] | None = None
    ) -> str:
        """横向对比多家公司同一指标"""
        from repository.financial_repo import FinancialDataRepository
        from data.retriever import METRIC_ALIAS

        std_metric = METRIC_ALIAS.get(metric_name, metric_name)
        repo = FinancialDataRepository()
        rows = repo.compare_metric(db, std_metric, year, stock_codes)
        if not rows:
            return f"未找到 {year}年 {metric_name} 的对比数据"

        lines = [f"{year}年 {metric_name} 对比（从高到低）："]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"  {i}. {r.stock_name}（{r.stock_code}）：{r.metric_value}{r.metric_unit or ''}"
            )
        return "\n".join(lines)

    def calculate_risk_score(self, db, stock_code: str, year: int = 2024) -> str:
        """计算风险评分，返回格式化风险报告"""
        from repository.financial_repo import FinancialDataRepository
        from data.retriever import COMPANY_MAP

        if not stock_code.isdigit():
            stock_code = COMPANY_MAP.get(stock_code, stock_code)

        repo = FinancialDataRepository()
        rows = repo.get_by_company_year(db, stock_code, year)
        if not rows:
            years = repo.get_company_years(db, stock_code)
            if not years:
                return f"未找到 {stock_code} 的财务数据"
            year = years[0]
            rows = repo.get_by_company_year(db, stock_code, year)

        stock_name = rows[0].stock_name
        data = {r.metric_name: float(r.metric_value) for r in rows if r.metric_value is not None}

        risk_items = []
        score = 100  # 从满分扣减

        debt = data.get("资产负债率")
        if debt is not None:
            if debt > 60:
                risk_items.append(f"⚠️ 资产负债率偏高（{debt:.1f}%），财务风险较大")
                score -= 20
            elif debt > 45:
                risk_items.append(f"⚡ 资产负债率中等（{debt:.1f}%），需关注")
                score -= 10

        current = data.get("流动比率")
        if current is not None and current < 1.2:
            risk_items.append(f"⚠️ 流动比率偏低（{current:.2f}），短期偿债压力较大")
            score -= 15

        gross = data.get("毛利率")
        if gross is not None and gross < 35:
            risk_items.append(f"⚡ 毛利率偏低（{gross:.1f}%），盈利空间受压")
            score -= 10

        roe = data.get("ROE")
        if roe is not None and roe < 8:
            risk_items.append(f"⚡ ROE偏低（{roe:.1f}%），股东回报不足")
            score -= 10

        score = max(0, score)
        level = "低风险" if score >= 80 else "中等风险" if score >= 60 else "高风险"

        lines = [f"{stock_name}（{stock_code}）{year}年风险评分：{score}分（{level}）"]
        if risk_items:
            lines.append("风险信号：")
            lines.extend(f"  {item}" for item in risk_items)
        else:
            lines.append("  未发现明显风险信号，财务状况健康")
        return "\n".join(lines)

    def diagnose_company(self, db, stock_code: str, year: int = 2024) -> str:
        """企业运营诊断，返回格式化诊断报告"""
        from service.analysis_service import diagnose
        from data.retriever import COMPANY_MAP

        if not stock_code.isdigit():
            stock_code = COMPANY_MAP.get(stock_code, stock_code)

        result = diagnose(db, stock_code, year)
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
        """
        生成分析报告框架（供 LLM 填充）
        user_type: 投资者 / 管理者 / 监管机构
        """
        from service.analysis_service import diagnose, scan_risks
        from data.retriever import COMPANY_MAP

        if not stock_code.isdigit():
            stock_code = COMPANY_MAP.get(stock_code, stock_code)

        diag = diagnose(db, stock_code)
        risks = scan_risks(db, [stock_code])
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
            lines.append("风险信号：" + "；".join(
                r["signal"] + r["detail"] for r in risk_info["risks"]
            ))
        if risk_info.get("opportunities"):
            lines.append("机会信号：" + "；".join(
                o["signal"] + o["detail"] for o in risk_info["opportunities"]
            ))
        return "\n".join(lines)
