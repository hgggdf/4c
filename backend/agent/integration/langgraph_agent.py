"""
基于 LangGraph 的真正 ReAct Agent。

LLM 自主决定调用哪些工具、调用几次，直到信息足够再输出最终答案。
与 GLMMinimalAgent 的区别：工具调用顺序和次数由 Kimi 决定，不是硬编码。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import get_settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 工具定义：用 @tool 把现有工具函数包一层，补充 LangChain 需要的类型注解
# ─────────────────────────────────────────────────────────────

@tool
def tool_resolve_company(text: str) -> list[dict]:
    """从公司名称、简称或别名识别公司，返回股票代码和基本信息。
    当用户提到公司名但没有给出股票代码时，先调这个工具。"""
    from agent.tools import resolve_company_from_text
    return resolve_company_from_text(text)


@tool
def tool_get_company_overview(stock_code: str) -> dict:
    """获取公司完整概览：基本信息、业务描述、核心产品、市场地位。
    参数 stock_code 为6位数字股票代码，如 '600276'。"""
    from agent.tools import get_company_overview
    return get_company_overview(stock_code)


@tool
def tool_get_financial_summary(stock_code: str, period_count: int = 4) -> dict:
    """获取财务数据汇总：最近N期利润表、资产负债表、现金流量表和关键指标（毛利率、ROE等）。
    参数 stock_code 为6位数字股票代码。period_count 默认4期。"""
    from agent.tools import get_financial_summary
    return get_financial_summary(stock_code, period_count=period_count)


@tool
def tool_get_financial_metrics(stock_code: str, metric_names: list[str], limit: int = 4) -> list[dict]:
    """获取指定财务指标的历史数据。
    metric_names 可选值：gross_margin（毛利率）、net_margin（净利率）、roe（净资产收益率）、
    rd_ratio（研发费用率）、debt_ratio（资产负债率）。
    参数 stock_code 为6位数字股票代码。"""
    from agent.tools import get_financial_metrics
    return get_financial_metrics(stock_code, metric_names, limit=limit)


@tool
def tool_get_company_event_summary(stock_code: str, days: int = 365) -> dict:
    """获取公司近期所有事件汇总：药品批准、临床试验、集采中标、监管风险，并按机会/风险/中性分类。
    参数 stock_code 为6位数字股票代码。days 默认365天。"""
    from agent.tools import get_company_event_summary
    return get_company_event_summary(stock_code, days=days)


@tool
def tool_get_drug_approvals(stock_code: str, days: int = 365) -> list[dict]:
    """获取药品批准事件：药品名称、批准类型、适应症、是否创新药、市场范围。
    适用于医药公司研发管线分析。参数 stock_code 为6位数字股票代码。"""
    from agent.tools import get_drug_approvals
    return get_drug_approvals(stock_code, days=days)


@tool
def tool_get_clinical_trials(stock_code: str, days: int = 365) -> list[dict]:
    """获取临床试验事件：药品名称、试验阶段（I/II/III期）、事件类型（启动/完成/中止）。
    参数 stock_code 为6位数字股票代码。"""
    from agent.tools import get_clinical_trials
    return get_clinical_trials(stock_code, days=days)


@tool
def tool_get_company_news_impact(stock_code: str, days: int = 90) -> dict:
    """获取公司新闻舆情汇总：新闻列表、影响方向统计（正面/负面/中性）、平均影响强度。
    参数 stock_code 为6位数字股票代码。days 默认90天。"""
    from agent.tools import get_company_news_impact
    return get_company_news_impact(stock_code, days=days)


@tool
def tool_search_company_evidence(query: str, stock_code: str, top_k: int = 5) -> list[dict]:
    """对公司相关文档（公告、财务附注）做语义检索，返回最相关的文本片段。
    query 为检索问题，如'研发管线进展'、'集采影响'。
    参数 stock_code 为6位数字股票代码。"""
    from agent.tools import search_company_evidence
    return search_company_evidence(query, stock_code, top_k=top_k)


@tool
def tool_get_macro_summary(indicator_names: list[str], recent_n: int = 6) -> dict:
    """获取宏观经济指标的时间序列数据。
    indicator_names 可选：GDP增速、CPI、PMI、医药制造业增加值等。recent_n 默认6期。"""
    from agent.tools import get_macro_summary
    return get_macro_summary(indicator_names, recent_n=recent_n)


# 注册到 Agent 的工具列表
AGENT_TOOLS = [
    tool_resolve_company,
    tool_get_company_overview,
    tool_get_financial_summary,
    tool_get_financial_metrics,
    tool_get_company_event_summary,
    tool_get_drug_approvals,
    tool_get_clinical_trials,
    tool_get_company_news_impact,
    tool_search_company_evidence,
    tool_get_macro_summary,
]


# ─────────────────────────────────────────────────────────────
# LangGraph Agent
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个专业的医药行业投研分析助手。

你可以调用以下工具获取真实数据：
- tool_resolve_company：从公司名识别股票代码
- tool_get_company_overview：公司基本信息和业务描述
- tool_get_financial_summary：财务三表和关键指标
- tool_get_financial_metrics：指定财务指标历史数据
- tool_get_company_event_summary：公司事件汇总（药批/临床/集采/监管）
- tool_get_drug_approvals：药品批准详情
- tool_get_clinical_trials：临床试验详情
- tool_get_company_news_impact：新闻舆情分析
- tool_search_company_evidence：语义检索公告和财务附注
- tool_get_macro_summary：宏观经济指标

工作原则：
1. 先用 tool_resolve_company 把公司名转成股票代码，再调其他工具
2. 根据问题类型选择合适的工具，不要调用无关工具
3. 只基于工具返回的真实数据作答，禁止编造数据
4. 数据不足时明确说明，不猜测
5. 用中文回答，保持专业简洁"""


class LangGraphAgent:
    """基于 LangGraph ReAct 的真正智能体，LLM 自主决定工具调用顺序和次数。"""

    framework = "langgraph"
    agent_mode = "kimi-react"

    # kimi-k2.5 开启了 thinking 模式，LangChain 多轮 tool-calling 时无法携带
    # reasoning_content，会触发 400。用 moonshot-v1-8k 作为 tool-calling 专用模型。
    TOOL_CALLING_MODEL = "moonshot-v1-8k"

    def __init__(self) -> None:
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.TOOL_CALLING_MODEL,
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            temperature=0.3,
            max_tokens=4096,
        )
        self._graph = create_react_agent(
            self.llm,
            tools=AGENT_TOOLS,
            prompt=SYSTEM_PROMPT,
        )

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.kimi_api_key and settings.kimi_model)

    def run(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """同步运行 Agent，返回最终答案和工具调用记录。"""
        messages = self._build_messages(message, history)
        config = {"recursion_limit": max_iterations * 2 + 4}

        try:
            result = self._graph.invoke({"messages": messages}, config=config)
        except Exception as exc:
            logger.exception("LangGraphAgent run error")
            return {
                "answer": f"Agent 执行出错：{exc}",
                "tool_calls": [],
                "framework": self.framework,
                "agent_mode": self.agent_mode,
            }

        return self._parse_result(result)

    def stream(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        max_iterations: int = 10,
    ):
        """流式运行 Agent，逐步 yield 工具调用过程和最终答案。"""
        messages = self._build_messages(message, history)
        config = {"recursion_limit": max_iterations * 2 + 4}

        for chunk in self._graph.stream({"messages": messages}, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                msgs = update.get("messages", [])
                for msg in msgs:
                    if isinstance(msg, AIMessage):
                        # LLM 决定调用工具
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                yield {
                                    "type": "tool_call",
                                    "tool": tc["name"],
                                    "args": tc["args"],
                                }
                        # LLM 输出最终答案
                        elif msg.content:
                            yield {
                                "type": "answer",
                                "content": msg.content,
                            }
                    elif isinstance(msg, ToolMessage):
                        # 工具执行结果
                        yield {
                            "type": "tool_result",
                            "tool": msg.name,
                            "content": str(msg.content)[:200],
                        }

    def _build_messages(
        self, message: str, history: list[dict[str, Any]] | None
    ) -> list:
        msgs = []
        for item in (history or [])[-6:]:
            role = item.get("role", "user")
            content = str(item.get("content", ""))
            if role == "user":
                msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                msgs.append(AIMessage(content=content))
        msgs.append(HumanMessage(content=message))
        return msgs

    def _parse_result(self, result: dict) -> dict[str, Any]:
        messages = result.get("messages", [])
        answer = ""
        tool_calls: list[dict] = []

        for msg in messages:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls.append({"tool": tc["name"], "args": tc["args"]})
                elif msg.content:
                    answer = msg.content
            elif isinstance(msg, ToolMessage):
                # 把工具调用记录里补上结果摘要
                if tool_calls:
                    tool_calls[-1]["result_preview"] = str(msg.content)[:100]

        return {
            "answer": answer,
            "tool_calls": tool_calls,
            "framework": self.framework,
            "agent_mode": self.agent_mode,
        }


__all__ = ["LangGraphAgent", "AGENT_TOOLS"]
