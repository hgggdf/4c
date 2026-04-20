"""股票分析智能体主流程，负责意图识别、上下文拼装和大模型调用。"""

from __future__ import annotations

import requests
from sqlalchemy.orm import Session

from app.agent.prompt import SYSTEM_PROMPT
from app.agent.tools import AgentTools
from config import get_settings
from app.data.retriever import route_query, search_structured, search_unstructured, hybrid_search

# 触发诊断的关键词
_DIAGNOSE_KW = ["诊断", "评估", "打分", "综合分析", "运营分析", "运营评估", "怎么样", "如何"]
_RISK_KW     = ["风险", "预警", "危险", "集采", "负债", "风险扫描"]
_REPORT_KW   = ["生成报告", "分析报告", "投资报告", "出报告", "写报告"]
_COMPARE_KW  = ["对比", "比较", "横向", "哪家", "谁更"]


def _detect_intent(message: str) -> str:
    """返回意图：diagnose / risk / report / compare / default"""
    if any(kw in message for kw in _REPORT_KW):
        return "report"
    if any(kw in message for kw in _DIAGNOSE_KW):
        return "diagnose"
    if any(kw in message for kw in _RISK_KW):
        return "risk"
    if any(kw in message for kw in _COMPARE_KW):
        return "compare"
    return "default"


class StockAgent:
    """面向聊天场景的股票分析智能体。"""

    def __init__(self) -> None:
        self.tools = AgentTools()
        self.settings = get_settings()

    def _call_llm(self, messages: list[dict]) -> str:
        """调用大模型接口并返回纯文本回答。"""
        base_url = self.settings.anthropic_base_url.rstrip("/")
        resp = requests.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key": self.settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.settings.claude_model,
                "max_tokens": 2048,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    def _needs_news(self, message: str) -> bool:
        """根据问题关键词判断是否需要补充资讯或研报上下文。"""
        keywords = ["研报", "研究", "资讯", "新闻", "公告", "行业", "趋势", "政策", "集采", "医保", "管线"]
        return any(kw in message for kw in keywords)

    def run(self, message: str, history: list[dict] | None = None, db: Session | None = None) -> dict:
        """执行一次智能问答，按意图整合行情、公司资料、风险诊断和检索结果。"""
        symbol = self.tools.extract_symbol(message)
        quote = None
        context_parts: list[str] = []
        intent = _detect_intent(message)

        # 子 Agent 1：本地公司数据仓 + 行情数据
        if symbol:
            dataset = self.tools.get_company_dataset(db, symbol, refresh=False, compact=True) if db is not None else None
            if dataset and dataset.get("quote"):
                quote = dataset["quote"]
            else:
                quote = self.tools.get_quote(symbol)

            if quote:
                context_parts.append(
                    f"【实时行情】{quote['name']}（{quote['symbol']}）"
                    f"最新价 {quote['price']}，涨跌额 {quote['change']}，"
                    f"涨跌幅 {quote['change_percent']}%，"
                    f"开盘 {quote['open']}，最高 {quote['high']}，最低 {quote['low']}，"
                    f"成交量 {quote['volume']}，时间 {quote['time']}"
                )

            company_context = self.tools.get_company_context(db, symbol) if db is not None else ""
            if company_context:
                context_parts.append(company_context)

        # 子 Agent 2：研报/资讯数据
        if self._needs_news(message) and not symbol:
            news = self.tools.get_pharma_news(symbol)
            valid = [n for n in news if "error" not in n and n.get("title")]
            if valid:
                news_lines = "\n".join(
                    f"- [{n['date']}] {n['title']} （{n['org']}）" for n in valid[:3]
                )
                context_parts.append(f"【相关研报/资讯】\n{news_lines}")

        # ── 子 Agent 3：意图路由工具调用 ──────────────────────────────────────
        if db is not None:
            try:
                if intent == "diagnose" and symbol:
                    result = self.tools.diagnose_company(db, symbol)
                    context_parts.append(f"【企业运营诊断】\n{result}")

                elif intent == "risk":
                    codes = [symbol] if symbol else ["600276", "603259", "300015"]
                    result = self.tools.calculate_risk_score(db, codes[0])
                    context_parts.append(f"【风险评估】\n{result}")

                elif intent == "report" and symbol:
                    user_type = "管理者" if "管理" in message else \
                                "监管" if "监管" in message else "投资者"
                    result = self.tools.generate_report(db, symbol, user_type)
                    context_parts.append(f"【报告生成指令】\n{result}")

                elif intent == "compare":
                    # 提取指标名
                    from app.data.retriever import METRIC_ALIAS
                    metric = next((k for k in METRIC_ALIAS if k in message), "毛利率")
                    result = self.tools.compare_companies(db, metric)
                    context_parts.append(f"【多公司对比】\n{result}")

                else:
                    # 默认：智能检索路由
                    query_type = route_query(message)
                    if query_type == "structured":
                        r = search_structured(db, message)
                        if r:
                            context_parts.append(f"【财务数据库查询结果】\n{r}")
                    elif query_type == "unstructured":
                        r = search_unstructured(message)
                        if r:
                            context_parts.append(f"【知识库相关内容】\n{r}")
                    else:
                        s, u = hybrid_search(db, message)
                        if s:
                            context_parts.append(f"【财务数据库查询结果】\n{s}")
                        if u:
                            context_parts.append(f"【知识库相关内容】\n{u}")

            except Exception:
                pass

        # ── 组装多轮对话历史 ──────────────────────────────────────────────────
        messages: list[dict] = []
        if history:
            for item in history[:-1]:
                if item.get("role") in ("user", "assistant") and item.get("content"):
                    messages.append({"role": item["role"], "content": item["content"]})

        user_content = message
        if context_parts:
            user_content = "\n".join(context_parts) + "\n\n用户问题：" + message

        messages.append({"role": "user", "content": user_content})

        try:
            answer = self._call_llm(messages)
        except Exception as e:
            answer = f"调用 AI 服务时出错：{e}\n请检查网络连接或 API Key 配置。"

        return {"answer": answer, "quote": quote, "symbol": symbol}
