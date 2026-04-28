"""
真正的 ReAct Agent：LLM 自主决定调哪些工具、调几次，直到信息足够再输出最终答案。

工具调用阶段用 moonshot-v1-8k（支持 function calling，无 thinking 限制）
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
            "name": "get_income_statements",
            "description": "获取利润表数据：营业收入、净利润、毛利润、研发费用等，支持多期历史数据。",
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
]

SYSTEM_PROMPT = """你是"医策经纬"——面向医药上市公司的多智能体运营诊断与投研辅助系统，具备真正的 Agent 能力。

工具选择指引：
- 问题涉及具体公司 → 先 resolve_company 获取股票代码，再调对应工具
- 问题是行业趋势、政策影响、宏观分析（无具体公司名）→ 直接调 search_documents，不要要求用户澄清
- 例如"集采对仿制药行业的影响" → search_documents(query="集采对仿制药的影响", doc_types=["announcement","news"])
- 例如"医保谈判最新政策" → search_documents(query="医保谈判政策", doc_types=["news","announcement"])

工作原则：
1. 用户提到公司名时，必须先调 resolve_company 获取股票代码，再调其他工具
2. 根据问题类型选择合适的工具，不要调用无关工具
3. 只基于工具返回的真实数据作答，不编造数据
4. 数据不足时明确说明，不猜测

最终答案要求：
- 引用具体数据数值，标注来源工具
- 说明推理过程和趋势判断
- 给出明确的投资决策建议
- 用中文回答，结构清晰"""


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

        return {"error": f"未知工具: {name}"}, "未知"

    except Exception as exc:
        logger.warning("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}, "执行失败"


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)[:3000]
    except Exception:
        return str(obj)[:3000]


# ─────────────────────────────────────────────────────────────
# ReAct Agent
# ─────────────────────────────────────────────────────────────

class ReactAgent:
    """真正的 ReAct Agent：工具调用用 moonshot-v1-8k，最终答案用 kimi-k2.5。"""

    MAX_ITERATIONS = 8
    TOOL_MODEL = "moonshot-v1-8k"

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
                    tool_args = json.loads(tc.function.arguments)
                except Exception:
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
                all_tool_results.append(f"[{tool_name} | {source}]\n{result_str[:2000]}")

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
                    "4. 用中文回答，结构清晰。"
                )
                final_messages = [
                    {"role": "system", "content": "你是专业的医药行业投研分析助手。以下工具数据均已成功从数据库获取，是真实可信的，请直接基于这些数据进行分析。"},
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
