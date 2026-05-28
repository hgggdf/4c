"""
真正的 ReAct Agent：LLM 自主决定调哪些工具、调几次，直到信息足够再输出最终答案。

工具调用阶段用 moonshot-v1-32k（支持 function calling，无 thinking 限制）
最终答案生成用 kimi-k2.5（更强的推理和写作能力）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Generator

from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 工具 Schema
# ─────────────────────────────────────────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "resolve_company",
            "description": "从公司名称、简称或别名识别公司，返回股票代码。当用户提到公司名但没有给出股票代码时，必须先调这个工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "公司名称、简称或别名，如'恒瑞'、'恒瑞医药'"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_overview",
            "description": "获取公司完整概览：基本信息、业务描述、核心产品、市场地位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码，如'600276'"}
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_summary",
            "description": "获取财务数据汇总：最近N期利润表（营业收入、净利润、毛利润、营业成本、销售费用、管理费用、研发费用、每股收益）、资产负债表（总资产、总负债）、现金流量表（经营/投资/筹资现金流）和关键指标（毛利率、净利率、ROE、资产负债率）。这是获取公司完整财务数据的首选工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "period_count": {"type": "integer", "description": "返回期数，默认4", "default": 4},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_income_statements",
            "description": "获取利润表数据：营业收入、营业成本、毛利润、销售费用、管理费用、研发费用、营业利润、净利润、扣非净利润、每股收益，支持多期历史数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "limit": {"type": "integer", "description": "返回期数，默认4", "default": 4},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance_sheets",
            "description": "获取资产负债表数据：总资产、总负债、资产负债率，支持多期历史数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "limit": {"type": "integer", "description": "返回期数，默认4", "default": 4},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cashflow_statements",
            "description": "获取现金流量表数据：经营活动现金流、投资活动现金流、筹资活动现金流，支持多期历史数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "limit": {"type": "integer", "description": "返回期数，默认4", "default": 4},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_metrics",
            "description": "获取关键财务指标历史数据：毛利率(gross_margin)、净利率(net_margin)、ROE、研发费用率(rd_ratio)、资产负债率(debt_ratio)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "metric_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "指标名称列表，可选：gross_margin, net_margin, roe, rd_ratio, debt_ratio",
                    },
                },
                "required": ["stock_code", "metric_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drug_approvals",
            "description": "获取药品批准事件：药品名称、批准类型、适应症、是否创新药。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "查询最近N天，默认365", "default": 365},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clinical_trials",
            "description": "获取临床试验事件：药品名称、试验阶段（I/II/III期）、事件类型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "查询最近N天，默认365", "default": 365},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_procurement_events",
            "description": "获取集采/采购事件：集采批次、中标情况、降价幅度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_news_impact",
            "description": "获取公司新闻舆情汇总：新闻列表、影响方向统计（正面/负面/中性）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "查询最近N天，默认90", "default": 90},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "对公告、财务附注、研报做语义检索，返回最相关的文本片段及来源文件。无需股票代码，适合行业政策、宏观趋势等问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题，如'集采对仿制药的影响'、'医保谈判政策'"},
                    "stock_code": {"type": "string", "description": "6位数字股票代码（可选，有具体公司时传入）"},
                    "doc_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文档类型过滤（可选），可选值：announcement、news、research_report",
                    },
                    "industry_code": {"type": "string", "description": "行业代码过滤（可选），如'医药生物'"},
                    "top_k": {"type": "integer", "description": "返回条数，默认5", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_event_summary",
            "description": "获取公司近期所有事件汇总：药品批准、临床试验、集采中标、监管风险，按机会/风险/中性分类。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "查询最近N天，默认365", "default": 365},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_summary",
            "description": "获取宏观经济指标时间序列：GDP增速、CPI、PMI、医药制造业增加值等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "指标名称列表",
                    },
                    "recent_n": {"type": "integer", "description": "返回最近N期，默认6", "default": 6},
                },
                "required": ["indicator_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_valuation_metrics",
            "description": "计算公司核心估值指标：PE（市盈率）、PB（市净率）、PS（市销率）、PEG、EV/EBITDA，并给出综合估值结论（高估/合理/低估）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码，如'600276'"},
                    "current_price": {"type": "number", "description": "当前股价（元）。不传则自动取数据库最新收盘价。"},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dcf_valuation",
            "description": "基于历史自由现金流的DCF贴现现金流估值，计算每股内在价值和安全边际，采用Gordon增长模型计算终值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "wacc": {"type": "number", "description": "加权平均资本成本，默认0.10（10%）", "default": 0.10},
                    "terminal_growth": {"type": "number", "description": "永续增长率，默认0.03（3%）", "default": 0.03},
                    "forecast_years": {"type": "integer", "description": "预测年数，默认5年", "default": 5},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_valuation_comparison",
            "description": "对多家公司进行估值横向对比，基于PE/PB/PS/PEG/ROE给出综合吸引力排名和行业均值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表，最多8家，如['600276', '300760']",
                    },
                },
                "required": ["stock_codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_volume_data",
            "description": "获取公司日行情序列（OHLC、成交量、成交额、涨跌幅）。具体日期追问必须传 target_date，不要把日期误写成 days=1。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "返回交易日数，默认60；具体日期追问不要传1", "default": 60},
                    "target_date": {"type": "string", "description": "具体目标日期，如2026-05-08或5月8日"},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_volume_analysis",
            "description": "量价技术分析：计算MA5/10/20均线、量均线、量价Pearson相关系数、价格动量、识别放量上涨/放量下跌/缩量背离等量价信号，给出综合判断。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "分析窗口（交易日数），默认60", "default": 60},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_volume_event_correlation",
            "description": "量价异动与公司公告/新闻事件关联分析。找出近N日内的放量异动点（成交量>均量1.5倍且涨跌幅>3%），并检索前后3天内的公告和新闻，解释异动原因。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "days": {"type": "integer", "description": "回溯天数，默认120", "default": 120},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pipeline_drugs",
            "description": "列出公司在研管线品种，包含适应症、临床阶段、给药方式等信息。在做 rNPV 估值前先调此工具了解管线全貌。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                },
                "required": ["stock_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_pipeline_rnpv",
            "description": "计算单个管线品种的 rNPV（风险调整净现值）三情景估值（悲观/基准/乐观）。缺失参数有行业基准 fallback，不会报错。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "6位数字股票代码"},
                    "stock_name": {"type": "string", "description": "公司名称"},
                    "drug_name": {"type": "string", "description": "品种名称，不填则自动取管线第一个品种"},
                    "indication": {"type": "string", "description": "适应症，如'非小细胞肺癌'"},
                    "trial_phase": {"type": "string", "description": "临床阶段枚举：phase1/phase2/phase3/nda/approved"},
                    "route_of_administration": {"type": "string", "description": "给药方式，如'口服'/'注射'"},
                    "target_patients_wan": {"type": "number", "description": "目标患者数（万人），缺失时用行业基准"},
                    "price_per_year_wan": {"type": "number", "description": "年治疗费用（万元/人），缺失时用行业基准"},
                    "peak_market_share": {"type": "number", "description": "峰值市场份额 0-1，缺失时用行业基准"},
                    "net_margin": {"type": "number", "description": "净利润率 0-1，默认0.25"},
                    "wacc": {"type": "number", "description": "折现率 0-1，默认0.10"},
                    "rd_expense_total_wan": {"type": "number", "description": "公司整体R&D费用（万元），用于成本代理，可不填"},
                },
                "required": ["stock_code", "stock_name"],
            },
        },
    },
]

MARKDOWN_FORMULA_RULES = """Formatting rules:
- Use GitHub Markdown only. Do not output LaTeX math.
- Do not use $...$, $$...$$, \\(...\\), \\[...\\], \\frac{}, \\times, \\sum, or other TeX syntax.
- Write formulas as plain text or inline code, for example: `PE = stock price / EPS`, `FCF = operating cash flow - capex`.
- Prefer Markdown tables for formulas, assumptions, metrics, and conclusions; put units in table columns."""

SYSTEM_PROMPT = """你是"医策经纬"——面向医药上市公司的多智能体运营诊断与投研辅助系统，具备真正的 Agent 能力。

工具选择指引：
- 问题涉及具体公司 → 先 resolve_company 获取股票代码，再调对应工具
- 需要全面财务分析 → 优先调 get_financial_summary，它一次返回利润表+资产负债表+现金流量表+关键指标
- 需要单项财务数据 → 分别调 get_income_statements / get_balance_sheets / get_cashflow_statements
- 需要估值分析（PE/PB/PS/PEG/EV-EBITDA）→ 调 get_valuation_metrics
- 需要DCF内在价值估算 → 调 get_dcf_valuation
- 需要多家公司估值横向对比 → 调 get_valuation_comparison，传入股票代码列表
- 需要量价分析、技术面判断 → 调 get_price_volume_analysis
- 需要解释放量/缩量/异动原因 → 调 get_price_volume_event_correlation
- 需要获取原始日行情序列 → 调 get_price_volume_data
- 用户问“5月8日呢？”这类具体日期追问 → 调 get_price_volume_data，并传 target_date="5月8日"；不要传 days=1
- 需要管线 rNPV 估值 → 先调 list_pipeline_drugs 了解管线，再调 calculate_pipeline_rnpv 计算三情景估值
- 问题是行业趋势、政策影响、宏观分析（无具体公司名）→ 直接调 search_documents，不要要求用户澄清
- 例如"集采对仿制药行业的影响" → search_documents(query="集采对仿制药的影响", doc_types=["announcement","news"])
- 例如"医保谈判最新政策" → search_documents(query="医保谈判政策", doc_types=["news","announcement"])

工作原则：
1. 用户提到公司名时，必须先调 resolve_company 获取股票代码，再调其他工具
2. 根据问题类型选择合适的工具，不要调用无关工具
3. 只基于工具返回的真实数据作答，不编造数据
4. 数据不足时明确说明，不猜测
5. 用户明确指定了天数（如"最近120天"、"过去半年"、"250个交易日"等），必须将对应的整数值作为 days 参数传入工具，不得忽略或使用默认值
6. 用户指定具体日期（如"5月8日"、"2026-05-08"）时，这是 target_date，不是 days；不得把具体日期追问转换成 days=1

最终答案要求：
- 引用具体数据数值，标注来源工具
- 说明推理过程和趋势判断
- 给出明确的投资决策建议
- 用中文回答，结构清晰"""

SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + MARKDOWN_FORMULA_RULES


# ─────────────────────────────────────────────────────────────
# 工具执行器
# ─────────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict[str, Any]) -> tuple[Any, str]:
    """执行工具，返回 (结果, 数据来源描述)。"""
    try:
        if name == "resolve_company":
            from agent.tools import resolve_company_from_text
            result = resolve_company_from_text(args["text"])
            return result, "公司数据库"

        if name == "get_company_overview":
            from agent.tools import get_company_overview
            result = get_company_overview(args["stock_code"])
            return result, f"公司基础信息库 [{args['stock_code']}]"

        if name == "get_income_statements":
            from agent.tools import get_income_statements
            result = get_income_statements(args["stock_code"], limit=args.get("limit", 4))
            return result, f"财务数据库·利润表 [{args['stock_code']}]"

        if name == "get_financial_summary":
            from agent.tools import get_financial_summary
            result = get_financial_summary(args["stock_code"], period_count=args.get("period_count", 4))
            return result, f"财务数据库·财务汇总 [{args['stock_code']}]"

        if name == "get_balance_sheets":
            from agent.tools import get_balance_sheets
            result = get_balance_sheets(args["stock_code"], limit=args.get("limit", 4))
            return result, f"财务数据库·资产负债表 [{args['stock_code']}]"

        if name == "get_cashflow_statements":
            from agent.tools import get_cashflow_statements
            result = get_cashflow_statements(args["stock_code"], limit=args.get("limit", 4))
            return result, f"财务数据库·现金流量表 [{args['stock_code']}]"

        if name == "get_financial_metrics":
            from agent.tools import get_financial_metrics
            result = get_financial_metrics(args["stock_code"], args["metric_names"])
            return result, f"财务数据库·关键指标 [{args['stock_code']}]"

        if name == "get_drug_approvals":
            from agent.tools import get_drug_approvals
            result = get_drug_approvals(args["stock_code"], days=args.get("days", 365))
            return result, f"药品审批数据库 [{args['stock_code']}]"

        if name == "get_clinical_trials":
            from agent.tools import get_clinical_trials
            result = get_clinical_trials(args["stock_code"], days=args.get("days", 365))
            return result, f"临床试验数据库 [{args['stock_code']}]"

        if name == "get_procurement_events":
            from agent.tools import get_procurement_events
            result = get_procurement_events(args["stock_code"])
            return result, f"集采事件数据库 [{args['stock_code']}]"

        if name == "get_company_news_impact":
            from agent.tools import get_company_news_impact
            result = get_company_news_impact(args["stock_code"], days=args.get("days", 90))
            return result, f"新闻舆情数据库 [{args['stock_code']}]"

        if name == "search_documents":
            from agent.tools.retrieval_tools import search_documents
            stock_code = args.get("stock_code")
            result = search_documents(
                args["query"],
                stock_code=stock_code,
                doc_types=args.get("doc_types"),
                industry_code=args.get("industry_code"),
                top_k=args.get("top_k", 5),
            )
            source = f"向量检索库 [query='{args['query']}'"
            if stock_code:
                source += f", stock={stock_code}"
            if args.get("doc_types"):
                source += f", types={args['doc_types']}"
            source += "]"
            return result, source

        if name == "get_company_event_summary":
            from agent.tools import get_company_event_summary
            result = get_company_event_summary(args["stock_code"], days=args.get("days", 365))
            return result, f"事件汇总数据库 [{args['stock_code']}]"

        if name == "get_macro_summary":
            from agent.tools import get_macro_summary
            result = get_macro_summary(args["indicator_names"], recent_n=args.get("recent_n", 6))
            return result, f"宏观经济数据库 [{', '.join(args['indicator_names'])}]"

        if name == "get_valuation_metrics":
            from agent.tools import get_valuation_metrics
            result = get_valuation_metrics(args["stock_code"], current_price=args.get("current_price"))
            return result, f"估值分析 [{args['stock_code']}]"

        if name == "get_dcf_valuation":
            from agent.tools import get_dcf_valuation
            result = get_dcf_valuation(
                args["stock_code"],
                wacc=args.get("wacc", 0.10),
                terminal_growth=args.get("terminal_growth", 0.03),
                forecast_years=args.get("forecast_years", 5),
            )
            return result, f"DCF估值 [{args['stock_code']}]"

        if name == "get_valuation_comparison":
            from agent.tools import get_valuation_comparison
            result = get_valuation_comparison(args["stock_codes"])
            codes_str = ", ".join(args["stock_codes"])
            return result, f"估值横向对比 [{codes_str}]"

        if name == "get_price_volume_data":
            from agent.tools import get_price_volume_data
            requested_days = args.get("days", 60)
            try:
                effective_days = int(requested_days)
            except (TypeError, ValueError):
                effective_days = 60
            if effective_days < 30:
                effective_days = 60
            result = get_price_volume_data(
                args["stock_code"],
                days=effective_days,
                target_date=args.get("target_date"),
            )
            result["requested_days"] = requested_days
            result["effective_days"] = effective_days
            return result, f"日行情序列 [{args['stock_code']}]"

        if name == "get_price_volume_analysis":
            from agent.tools import get_price_volume_analysis
            result = get_price_volume_analysis(args["stock_code"], days=args.get("days", 60))
            return result, f"量价分析 [{args['stock_code']}]"

        if name == "get_price_volume_event_correlation":
            from agent.tools import get_price_volume_event_correlation
            result = get_price_volume_event_correlation(args["stock_code"], days=args.get("days", 120))
            return result, f"量价事件关联 [{args['stock_code']}]"

        if name == "list_pipeline_drugs":
            from agent.tools.rnpv_tools import list_pipeline_drugs
            result = list_pipeline_drugs(args["stock_code"])
            return result, f"管线数据库 [{args['stock_code']}]"

        if name == "calculate_pipeline_rnpv":
            from agent.tools.rnpv_tools import calculate_pipeline_rnpv
            result = calculate_pipeline_rnpv(
                stock_code=args["stock_code"],
                stock_name=args["stock_name"],
                drug_name=args.get("drug_name"),
                indication=args.get("indication"),
                trial_phase=args.get("trial_phase"),
                route_of_administration=args.get("route_of_administration"),
                target_patients_wan=args.get("target_patients_wan"),
                price_per_year_wan=args.get("price_per_year_wan"),
                peak_market_share=args.get("peak_market_share"),
                net_margin=args.get("net_margin", 0.25),
                wacc=args.get("wacc", 0.10),
                rd_expense_total_wan=args.get("rd_expense_total_wan"),
            )
            return result, f"rNPV 管线估值 [{args['stock_code']}]"

        return {"error": f"未知工具: {name}"}, "未知"

    except Exception as exc:
        logger.warning("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}, "执行失败"


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)[:6000]
    except Exception:
        return str(obj)[:6000]


# ─────────────────────────────────────────────────────────────
# ReAct Agent
# ─────────────────────────────────────────────────────────────

class ReactAgent:
    """真正的 ReAct Agent：工具调用用 moonshot-v1-32k，最终答案用 kimi-k2.5。"""

    MAX_ITERATIONS = 8
    TOOL_MODEL = "moonshot-v1-32k"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.kimi_api_key
        self._base_url = settings.kimi_base_url
        self._answer_model = settings.kimi_model  # kimi-k2.5

    def is_configured(self) -> bool:
        return bool(self._api_key and self._base_url)

    def stream(
        self,
        question: str,
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        if not self.is_configured():
            yield {"type": "error", "message": "LLM 未配置，请检查 KIMI_API_KEY / KIMI_BASE_URL"}
            return

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in (history or [])[-6:]:
            role = item.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": str(item.get("content", ""))})
        messages.append({"role": "user", "content": question})

        collected_sources: list[str] = []
        all_tool_results: list[str] = []
        iteration = 0

        for iteration in range(self.MAX_ITERATIONS):
            try:
                response = client.chat.completions.create(
                    model=self.TOOL_MODEL,
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=4096,
                )
            except Exception as exc:
                yield {"type": "error", "message": f"LLM 调用失败：{exc}"}
                return

            msg = response.choices[0].message

            if msg.content:
                yield {"type": "thinking", "content": msg.content}

            if not msg.tool_calls:
                break

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    logger.warning("Failed to parse tool arguments for %s: %r", tool_name, tc.function.arguments)
                    tool_args = {}

                yield {
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                    "call_id": tc.id,
                }

                result, source = _execute_tool(tool_name, tool_args)
                collected_sources.append(source)

                result_str = _safe_json(result)
                preview = result_str[:300] + ("..." if len(result_str) > 300 else "")
                all_tool_results.append(f"[{tool_name} | {source}]\n{result_str[:6000]}")

                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "call_id": tc.id,
                    "source": source,
                    "preview": preview,
                }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })
        else:
            yield {"type": "status", "content": "已达最大迭代次数，生成最终答案..."}

        yield {"type": "status", "content": "正在生成最终分析答案..."}
        try:
            if all_tool_results:
                synthesis_prompt = (
                    f"用户问题：{question}\n\n"
                    "以下数据已通过数据库工具成功获取，均为真实数据，请直接基于这些数据作答：\n\n"
                    + "\n\n".join(all_tool_results)
                    + "\n\n请给出专业分析，要求：\n"
                    "1. 直接引用上方数据中的具体数值，标注数据来源工具名；\n"
                    "2. 说明推理过程（数据说明了什么趋势/问题）；\n"
                    "3. 给出明确的投资决策建议（买入/持有/观望）及理由；\n"
                    "4. 用中文回答，结构清晰；\n"
                    "5. 公式必须使用普通 Markdown 文本或表格，禁止使用 LaTeX、$...$、$$...$$、\\frac{}、\\times 等 TeX 语法。"
                )
                final_messages = [
                    {"role": "system", "content": "你是专业的医药行业投研分析助手。以下工具数据均已成功从数据库获取，是真实可信的，请直接基于这些数据进行分析。\n\n" + MARKDOWN_FORMULA_RULES},
                    {"role": "user", "content": synthesis_prompt},
                ]
            else:
                final_messages = messages

            final_resp = client.chat.completions.create(
                model=self._answer_model,
                messages=final_messages,
                temperature=1,
                max_tokens=4096,
            )
            answer = final_resp.choices[0].message.content or ""
        except Exception as exc:
            answer = f"生成最终答案失败：{exc}"

        yield {
            "type": "answer",
            "content": answer,
            "sources": list(dict.fromkeys(collected_sources)),
            "iterations": iteration + 1,
        }


__all__ = ["ReactAgent"]
