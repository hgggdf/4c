from __future__ import annotations

from typing import Any


MODE_LABELS: dict[str, str] = {
    "company_analysis": "company_analysis",
    "financial_analysis": "financial_analysis",
    "pipeline_analysis": "pipeline_analysis",
    "policy_procurement": "policy_procurement",
    "risk_warning": "risk_warning",
    "industry_compare": "industry_compare",
    "chart_analysis": "chart_analysis",
    "report_generation": "report_generation",
    "quick_query": "quick_query",
}

ASCII_MODE_HINTS: dict[str, list[str]] = {
    "policy_procurement": ["drg", "dip", "vbp", "nr"],
    "pipeline_analysis": ["ind", "nda", "bla"],
    "financial_analysis": ["roe", "roa", "eps"],
}

MODE_ALIASES: dict[str, str] = {
    "公司分析": "company_analysis",
    "财务分析": "financial_analysis",
    "药品管线": "pipeline_analysis",
    "政策/集采": "policy_procurement",
    "政策集采": "policy_procurement",
    "风险预警": "risk_warning",
    "行业对比": "industry_compare",
    "图表分析": "chart_analysis",
    "报告生成": "report_generation",
    "快速查询": "quick_query",
}

MODE_KEYWORDS: dict[str, list[str]] = {
    "financial_analysis": [
        "财务",
        "营收",
        "收入",
        "净利润",
        "利润",
        "毛利率",
        "净利率",
        "现金流",
        "经营现金流",
        "研发费用率",
        "销售费用率",
        "roe",
        "同比",
        "环比",
        "年报",
        "季报",
    ],
    "pipeline_analysis": [
        "管线",
        "药品",
        "新药",
        "临床",
        "临床试验",
        "一期",
        "二期",
        "三期",
        "ind",
        "nda",
        "bla",
        "获批",
        "适应症",
        "研发进展",
        "创新药",
    ],
    "policy_procurement": [
        "集采",
        "带量采购",
        "医保",
        "医保谈判",
        "医保目录",
        "控费",
        "降价",
        "支付改革",
        "drg",
        "dip",
        "政策",
        "国家药监局",
        "药监局",
        "卫健委",
    ],
    "risk_warning": [
        "风险",
        "预警",
        "处罚",
        "监管",
        "负面",
        "暴雷",
        "诉讼",
        "违规",
        "质量问题",
        "召回",
        "问询函",
        "减值",
        "亏损",
        "舆情",
    ],
    "industry_compare": [
        "行业对比",
        "同行",
        "同业",
        "竞品",
        "竞对",
        "对比",
        "排名",
        "横向比较",
        "和谁比",
        "相比",
    ],
    "chart_analysis": [
        "图表",
        "画图",
        "趋势图",
        "柱状图",
        "雷达图",
        "时间线",
        "可视化",
        "展示趋势",
        "做个图",
    ],
    "report_generation": [
        "报告",
        "生成报告",
        "研报",
        "分析报告",
        "markdown",
        "汇总成文档",
        "写一份",
    ],
    "company_analysis": [
        "公司分析",
        "基本面",
        "经营情况",
        "主营业务",
        "商业模式",
        "公司怎么样",
        "值得关注吗",
        "投资价值",
        "综合分析",
    ],
}

MODE_PRIORITY = [
    "policy_procurement",
    "pipeline_analysis",
    "risk_warning",
    "financial_analysis",
    "industry_compare",
    "chart_analysis",
    "report_generation",
    "company_analysis",
    "quick_query",
]


def is_valid_mode(mode: str | None) -> bool:
    return bool(mode) and mode in MODE_LABELS


def normalize_mode(selected_mode: str | None) -> str | None:
    if not selected_mode:
        return None

    mode = str(selected_mode).strip()
    if not mode:
        return None

    if is_valid_mode(mode):
        return mode

    return MODE_ALIASES.get(mode)


def resolve_mode(user_question: str, selected_mode: str | None = None) -> str:
    normalized = normalize_mode(selected_mode)
    if normalized:
        return normalized

    text = str(user_question or "")
    lower_text = text.lower()
    hit_modes: set[str] = set()

    for mode, hints in ASCII_MODE_HINTS.items():
        for hint in hints:
            if hint in lower_text:
                hit_modes.add(mode)
                break

    for mode in MODE_PRIORITY:
        if mode == "quick_query":
            continue
        keywords = MODE_KEYWORDS.get(mode, [])
        for keyword in keywords:
            if keyword.isascii():
                if keyword in lower_text:
                    hit_modes.add(mode)
                    break
            elif keyword in text:
                hit_modes.add(mode)
                break

    for mode in MODE_PRIORITY:
        if mode in hit_modes:
            return mode

    return "quick_query"
