"""
基于 LangGraph 的真正 ReAct Agent。

LLM 自主决定调用哪些工具、调用几次，直到信息足够再输出最终答案。
与 GLMMinimalAgent 的区别：工具调用顺序和次数由 Kimi 决定，不是硬编码。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent, ToolNode
from openai import OpenAI

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
def tool_search_knowledge(
    query: str,
    doc_types: list[str] | None = None,
    industry_code: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """对全库文档做语义检索，无需股票代码。适用于行业政策、宏观趋势等无具体公司的问题。
    query 为检索问题，如'集采对仿制药的影响'、'医保谈判政策'。
    doc_types 可选过滤文档类型，如 ['announcement', 'news', 'research_report']。
    industry_code 可选按行业过滤，如 '医药生物'。"""
    from agent.tools.retrieval_tools import search_documents
    return search_documents(query, doc_types=doc_types, industry_code=industry_code, top_k=top_k)


@tool
def tool_get_macro_summary(indicator_names: list[str], recent_n: int = 6) -> dict:
    """获取宏观经济指标的时间序列数据。
    indicator_names 可选：GDP增速、CPI、PMI、医药制造业增加值等。recent_n 默认6期。"""
    from agent.tools import get_macro_summary
    return get_macro_summary(indicator_names, recent_n=recent_n)


@tool
def tool_compare_companies(stock_codes: list[str], metric_names: list[str], limit: int = 4) -> dict:
    """对比多家公司的财务指标。
    重要：stock_codes 必须是真实的6位数字股票代码列表，如 ['600276', '600196']。
    调用本工具前，必须先用 tool_resolve_company 把公司名转成股票代码，再把真实代码传入。
    metric_names 为指标名称列表，可选：gross_margin、net_margin、roe、rd_ratio、debt_ratio。
    limit 为每个指标返回最近N期数据，默认4期。"""
    import re
    # 过滤掉占位符，只保留真实6位数字股票代码
    valid_codes = [c for c in stock_codes if re.fullmatch(r"\d{6}", str(c))]
    if len(valid_codes) < 2:
        return {"error": f"需要至少2个有效的6位数字股票代码，收到: {stock_codes}。请先调用 tool_resolve_company 获取股票代码。"}
    from agent.tools.comparison_tools import compare_financial_metrics
    return compare_financial_metrics(valid_codes, metric_names, limit=limit)


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
    tool_search_knowledge,
    tool_get_macro_summary,
    tool_compare_companies,
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
- tool_search_company_evidence：语义检索特定公司的公告和财务附注（需要 stock_code）
- tool_search_knowledge：语义检索全库文档，无需股票代码，适合行业/政策类问题
- tool_get_macro_summary：宏观经济指标
- tool_compare_companies：对比多家公司的财务指标

工具选择指引：
- 问题涉及具体公司 → 先 tool_resolve_company 获取股票代码，再调对应工具
- 问题是行业趋势、政策影响、宏观分析（无具体公司名）→ 直接调 tool_search_knowledge，不要触发 [CLARIFY]
- 例如"集采对仿制药行业的影响"、"医保谈判最新政策" → tool_search_knowledge(query=..., doc_types=["announcement","news"])

工作原则：
1. 根据问题类型选择合适的工具，不要调用无关工具
2. 只基于工具返回的真实数据作答，禁止编造数据
3. 数据不足时明确说明，不猜测
4. 用中文回答，保持专业简洁

澄清规则：
- 仅当问题既没有公司名/股票代码，又不属于行业/政策类问题，且无法判断用户意图时，才回复：[CLARIFY] 请问您想了解哪方面的信息？
- 行业、政策、宏观类问题不需要澄清，直接调 tool_search_knowledge
- 时间范围不需要澄清，工具默认返回最近数期数据
- 只要能识别出公司，就直接调用工具查询，不要过度澄清"""


class LangGraphAgent:
    """基于 LangGraph ReAct 的真正智能体，采用双模型架构：
    - 工具调用阶段：moonshot-v1-8k（快速、稳定，LangChain）
    - 最终答案生成：kimi-k2.5（thinking 模型，原生 OpenAI SDK 直调）
    """

    framework = "langgraph"
    agent_mode = "kimi-react+thinking"

    TOOL_CALLING_MODEL = "moonshot-v1-8k"
    THINKING_MODEL = "kimi-k2.5"

    def __init__(self) -> None:
        settings = get_settings()
        self.tool_llm = ChatOpenAI(
            model=self.TOOL_CALLING_MODEL,
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            temperature=0.3,
            max_tokens=4096,
        )
        # 原生 OpenAI SDK，绕开 LangChain 的 reasoning_content 400 问题
        self._thinking_client = OpenAI(
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
        )
        self._graph = create_react_agent(
            self.tool_llm,
            tools=ToolNode(AGENT_TOOLS, handle_tool_errors=True),
            prompt=SYSTEM_PROMPT,
        )

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.kimi_api_key and settings.kimi_model)

    # ── 工具结果提取 ──────────────────────────────────────────

    def _extract_tool_results(self, messages: list) -> list[dict]:
        """从 LangGraph messages 提取 [{tool, args, result}]。"""
        results = []
        pending: dict[str, dict] = {}  # tool_call_id -> {tool, args}

        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}
            elif isinstance(msg, ToolMessage):
                info = pending.pop(msg.tool_call_id, None)
                if info:
                    results.append({
                        "tool": info["tool"],
                        "args": info["args"],
                        "result": msg.content,
                    })
        return results

    # ── 合成 prompt 构建 ──────────────────────────────────────

    def _build_synthesis_messages(
        self,
        collected_data: list[dict],
        question: str,
        history: list[dict[str, Any]] | None,
        system_context: str | None = None,
    ) -> list[dict]:
        data_sections = []
        for i, item in enumerate(collected_data, 1):
            args_json = json.dumps(item["args"], ensure_ascii=False, default=str)
            result_str = item["result"] if isinstance(item["result"], str) else json.dumps(item["result"], ensure_ascii=False, default=str)
            data_sections.append(
                f"### 数据源 {i}：{item['tool']}\n"
                f"调用参数：{args_json}\n"
                f"返回数据：\n{result_str[:2000]}"
            )

        history_text = ""
        for h in (history or [])[-6:]:
            role = "用户" if h.get("role") == "user" else "助手"
            history_text += f"{role}：{h.get('content', '')}\n"

        user_content = (
            f"## 用户问题\n{question}\n\n"
            + (f"## 对话历史\n{history_text}\n" if history_text else "")
            + f"## 数据采集结果（共 {len(collected_data)} 个数据源）\n\n"
            + "\n\n".join(data_sections)
        )

        system_content = (
            (system_context + "\n\n" if system_context else "")
            + "你是专业的医药行业投研分析助手。"
            "请基于上方工具采集的真实数据进行深度分析，禁止编造数据，用中文回答，结构清晰。"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    # ── thinking 模型调用（同步）────────────────────────────

    def _synthesize_with_thinking(
        self,
        collected_data: list[dict],
        question: str,
        history: list[dict[str, Any]] | None = None,
        system_context: str | None = None,
    ) -> str:
        msgs = self._build_synthesis_messages(collected_data, question, history, system_context)
        response = self._thinking_client.chat.completions.create(
            model=self.THINKING_MODEL,
            messages=msgs,
            temperature=1.0,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    # ── thinking 模型调用（流式）────────────────────────────

    def _synthesize_with_thinking_stream(
        self,
        collected_data: list[dict],
        question: str,
        history: list[dict[str, Any]] | None = None,
        system_context: str | None = None,
    ) -> Generator[str, None, None]:
        msgs = self._build_synthesis_messages(collected_data, question, history, system_context)
        stream = self._thinking_client.chat.completions.create(
            model=self.THINKING_MODEL,
            messages=msgs,
            temperature=1.0,
            max_tokens=4096,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ── 公共接口 ─────────────────────────────────────────────

    def run(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_context: str | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        messages = self._build_messages(message, history, system_context=system_context)
        config = {"recursion_limit": max_iterations * 2 + 4}

        try:
            result = self._graph.invoke({"messages": messages}, config=config)
            parsed = self._parse_result(result, message)
            collected_data = self._extract_tool_results(result.get("messages", []))

            if collected_data:
                try:
                    answer = self._synthesize_with_thinking(
                        collected_data, message, history, system_context
                    )
                    parsed["answer"] = answer
                    parsed["thinking_used"] = True
                except Exception as exc:
                    logger.warning("kimi-k2.5 synthesis failed, falling back: %s", exc)
                    parsed["thinking_used"] = False
                    # 降级：用 moonshot 的原始答案
                    if not parsed.get("answer"):
                        for msg in reversed(result.get("messages", [])):
                            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                                parsed["answer"] = msg.content
                                break
            else:
                parsed["thinking_used"] = False

            return parsed

        except Exception as exc:
            logger.exception("LangGraphAgent run error")
            return {
                "answer": f"Agent 执行出错：{exc}",
                "tool_calls": [],
                "framework": self.framework,
                "agent_mode": self.agent_mode,
                "thinking_used": False,
            }

    def stream(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_context: str | None = None,
        max_iterations: int = 10,
    ):
        messages = self._build_messages(message, history, system_context=system_context)
        config = {"recursion_limit": max_iterations * 2 + 4}

        all_messages: list = []
        tool_call_count = 0

        # 阶段一：moonshot-v1-8k 执行 ReAct 工具调用循环
        for chunk in self._graph.stream({"messages": messages}, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                msgs = update.get("messages", [])
                all_messages.extend(msgs)
                for msg in msgs:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_call_count += 1
                            yield {"type": "tool_call", "tool": tc["name"], "args": tc["args"]}
                    elif isinstance(msg, ToolMessage):
                        yield {
                            "type": "tool_result",
                            "tool": msg.name,
                            "content": str(msg.content)[:200],
                        }

        # 过渡
        yield {"type": "synthesizing"}

        # 阶段二：kimi-k2.5 流式生成最终答案
        collected_data = self._extract_tool_results(all_messages)

        if collected_data:
            try:
                for chunk_text in self._synthesize_with_thinking_stream(
                    collected_data, message, history, system_context
                ):
                    yield {"type": "answer_chunk", "content": chunk_text}
            except Exception as exc:
                logger.warning("kimi-k2.5 stream failed, falling back: %s", exc)
                # 降级：返回 moonshot 原始答案
                for msg in reversed(all_messages):
                    if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                        yield {"type": "answer_chunk", "content": msg.content}
                        break
        else:
            # 无工具调用，直接输出 moonshot 的回答
            for msg in all_messages:
                if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                    yield {"type": "answer_chunk", "content": msg.content}
                    break

        yield {"type": "answer_done"}

    def _build_messages(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        *,
        system_context: str | None = None,
    ) -> list:
        msgs = []
        if system_context:
            msgs.append(SystemMessage(content=system_context))
        for item in (history or [])[-6:]:
            role = item.get("role", "user")
            content = str(item.get("content", ""))
            if role == "user":
                msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                msgs.append(AIMessage(content=content))
        msgs.append(HumanMessage(content=message))
        return msgs

    def _parse_result(self, result: dict, original_question: str = "") -> dict[str, Any]:
        messages = result.get("messages", [])
        answer = ""
        tool_calls: list[dict] = []
        clarification_needed = False
        clarification_question = ""

        for msg in messages:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls.append({"tool": tc["name"], "args": tc["args"]})
                elif msg.content:
                    answer = msg.content
                    # 检测澄清标记
                    if "[CLARIFY]" in answer:
                        clarification_needed = True
                        clarification_question = answer.replace("[CLARIFY]", "").strip()
                        answer = ""
            elif isinstance(msg, ToolMessage):
                if tool_calls:
                    tool_calls[-1]["result_preview"] = str(msg.content)[:100]

        return {
            "answer": answer,
            "tool_calls": tool_calls,
            "framework": self.framework,
            "agent_mode": self.agent_mode,
            "clarification_needed": clarification_needed,
            "clarification_question": clarification_question,
        }



__all__ = ["LangGraphAgent", "AGENT_TOOLS"]
