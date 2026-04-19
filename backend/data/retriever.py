"""
智能检索路由：判断用户问题应查结构化数据（SQL）还是非结构化研报（向量检索）
"""
from __future__ import annotations

import re
from sqlalchemy.orm import Session

from data.knowledge_store import get_vector_store, get_store
from repository.financial_repo import FinancialDataRepository
from repository.macro_repo import MacroIndicatorRepository

# 结构化查询关键词
STRUCTURED_KEYWORDS = [
    "毛利率", "净利润", "营业收入", "营业总收入", "ROE", "净资产收益率",
    "资产负债率", "每股收益", "研发投入", "研发费用", "净利率",
    "流动比率", "速动比率", "存货周转", "应收账款",
    "多少", "是多少", "几亿", "增长了", "下降了", "同比",
    "CPI", "GDP", "宏观",
]

# 非结构化（研报/分析）关键词
UNSTRUCTURED_KEYWORDS = [
    "分析", "研报", "前景", "风险", "机会", "投资价值",
    "管线", "集采", "医保", "政策", "竞争", "赛道", "行业",
    "为什么", "原因", "影响", "建议", "看法", "怎么样",
]

# 强结构化信号：出现这些词时直接走 structured，不管 unstructured 得分
FORCE_STRUCTURED = [
    "近三年", "近几年", "历年", "趋势", "变化", "增长率",
    "多少", "是多少", "几亿", "同比",
]

# 公司名称 -> 股票代码
COMPANY_MAP = {
    "恒瑞": "600276", "恒瑞医药": "600276",
    "药明": "603259", "药明康德": "603259",
    "爱尔": "300015", "爱尔眼科": "300015",
}

METRIC_ALIAS = {
    "毛利率": "毛利率",
    "净利润": "净利润",
    "营业收入": "营业总收入",
    "营业总收入": "营业总收入",
    "净资产收益率": "ROE",
    "ROE": "ROE",
    "资产负债率": "资产负债率",
    "每股收益": "每股收益",
    "净利率": "净利率",
    "研发投入": "研发投入",
    "研发费用": "研发投入",
    "流动比率": "流动比率",
    "速动比率": "速动比率",
}


def _extract_year(text: str) -> int | None:
    m = re.search(r"(202[0-9]|201[0-9])", text)
    return int(m.group(1)) if m else None


def _extract_company(text: str) -> tuple[str | None, str | None]:
    """返回 (stock_code, company_name)"""
    for name, code in COMPANY_MAP.items():
        if name in text:
            return code, name
    return None, None


def _extract_metric(text: str) -> str | None:
    for alias, standard in METRIC_ALIAS.items():
        if alias in text:
            return standard
    return None


def route_query(query: str) -> str:
    """判断查询类型：'structured' | 'unstructured' | 'hybrid'"""
    # 强结构化信号优先
    if any(kw in query for kw in FORCE_STRUCTURED):
        if any(kw in query for kw in UNSTRUCTURED_KEYWORDS):
            return "hybrid"
        return "structured"

    s_score = sum(1 for kw in STRUCTURED_KEYWORDS if kw in query)
    u_score = sum(1 for kw in UNSTRUCTURED_KEYWORDS if kw in query)

    if s_score > 0 and u_score == 0:
        return "structured"
    if u_score > 0 and s_score == 0:
        return "unstructured"
    if s_score > 0 and u_score > 0:
        return "hybrid"
    return "unstructured"


def search_structured(db: Session, query: str) -> str | None:
    """从 financial_data / macro_indicator 查结构化数据，返回格式化文本"""
    repo = FinancialDataRepository()
    macro_repo = MacroIndicatorRepository()

    code, company_name = _extract_company(query)
    year = _extract_year(query)
    metric = _extract_metric(query)

    lines = []

    # 宏观数据查询
    if any(kw in query for kw in ["CPI", "GDP", "宏观", "经济"]):
        for indicator in ["CPI同比增长率", "医疗保健CPI同比增长率", "GDP同比增长率"]:
            series = macro_repo.get_series(db, indicator)
            if series:
                recent = series[-3:]
                vals = ", ".join(f"{r.period}:{r.value}{r.unit}" for r in recent)
                lines.append(f"{indicator}（近期）：{vals}")

    # 单指标查询
    if code and metric and year:
        row = repo.get_metric(db, code, year, metric)
        if row:
            lines.append(
                f"{row.stock_name}（{row.stock_code}）{row.year}年 {row.metric_name}："
                f"{row.metric_value}{row.metric_unit or ''}"
                f"（来源：{row.source or '年报'}）"
            )

    # 某公司某年全部指标
    elif code and year and not metric:
        rows = repo.get_by_company_year(db, code, year)
        if rows:
            lines.append(f"{rows[0].stock_name}（{code}）{year}年核心财务指标：")
            for r in rows:
                lines.append(f"  {r.metric_name}: {r.metric_value}{r.metric_unit or ''}")

    # 某公司近3年某指标趋势
    elif code and metric and not year:
        for y in [2022, 2023, 2024]:
            row = repo.get_metric(db, code, y, metric)
            if row:
                lines.append(
                    f"{row.stock_name} {y}年 {metric}：{row.metric_value}{row.metric_unit or ''}"
                )

    # 多公司横向对比
    if metric and not code:
        rows = repo.compare_metric(db, metric, year or 2024)
        if rows:
            lines.append(f"{year or 2024}年 {metric} 对比：")
            for r in rows:
                lines.append(f"  {r.stock_name}（{r.stock_code}）：{r.metric_value}{r.metric_unit or ''}")

    return "\n".join(lines) if lines else None


def search_unstructured(query: str, top_k: int = 3) -> str | None:
    """向量检索研报/背景知识，返回格式化文本"""
    try:
        store = get_vector_store()
        if store.count() == 0:
            # 兜底用 TF-IDF
            tfidf = get_store()
            hits = tfidf.search(query, top_k=top_k)
        else:
            hits = store.search(query, top_k=top_k)

        if not hits:
            return None

        parts = []
        for h in hits:
            src = h["meta"].get("source", "知识库")
            parts.append(f"[来源: {src}（相似度{h['score']}）]\n{h['text']}")
        return "\n\n".join(parts)
    except Exception:
        return None


def hybrid_search(db: Session, query: str) -> tuple[str | None, str | None]:
    """同时查结构化和非结构化，返回 (structured_result, unstructured_result)"""
    return search_structured(db, query), search_unstructured(query)
