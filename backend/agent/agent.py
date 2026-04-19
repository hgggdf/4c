from __future__ import annotations

import requests

from agent.prompt import SYSTEM_PROMPT
from agent.tools import AgentTools
from config import get_settings
from data.knowledge_store import get_store


class StockAgent:
    def __init__(self) -> None:
        self.tools = AgentTools()
        self.settings = get_settings()

    def _call_claude(self, messages: list[dict]) -> str:
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
        keywords = ["研报", "研究", "资讯", "新闻", "公告", "行业", "趋势", "政策", "集采", "医保", "管线"]
        return any(kw in message for kw in keywords)

    def run(self, message: str, history: list[dict] | None = None) -> dict:
        symbol = self.tools.extract_symbol(message)
        quote = None
        context_parts: list[str] = []

        # 子 Agent 1：行情数据
        if symbol:
            quote = self.tools.get_quote(symbol)
            context_parts.append(
                f"【实时行情】{quote['name']}（{quote['symbol']}）"
                f"最新价 {quote['price']}，涨跌额 {quote['change']}，"
                f"涨跌幅 {quote['change_percent']}%，"
                f"开盘 {quote['open']}，最高 {quote['high']}，最低 {quote['low']}，"
                f"成交量 {quote['volume']}，时间 {quote['time']}"
            )

        # 子 Agent 2：研报/资讯数据
        if self._needs_news(message) or symbol:
            news = self.tools.get_pharma_news(symbol)
            valid = [n for n in news if "error" not in n and n.get("title")]
            if valid:
                news_lines = "\n".join(
                    f"- [{n['date']}] {n['title']} （{n['org']}）" for n in valid[:3]
                )
                context_parts.append(f"【相关研报/资讯】\n{news_lines}")

        # 子 Agent 3：知识库 RAG 检索
        try:
            store = get_store()
            rag_hits = store.search(message, top_k=3)
            if rag_hits:
                rag_lines = "\n\n".join(
                    f"[来源: {h['meta'].get('source', '知识库')}]\n{h['text']}" for h in rag_hits
                )
                context_parts.append(f"【知识库相关内容】\n{rag_lines}")
        except Exception:
            pass

        # 组装多轮对话历史
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
            answer = self._call_claude(messages)
        except Exception as e:
            answer = f"调用 AI 服务时出错：{e}\n请检查网络连接或 API Key 配置。"

        return {"answer": answer, "quote": quote, "symbol": symbol}
