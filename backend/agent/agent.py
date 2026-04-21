"""LangChain 智能体占位实现。"""

from __future__ import annotations

from typing import Any


class LangChainAgentStub:
    """为后续 LangChain 智能体接入保留统一入口。"""

    framework = "langchain"
    agent_mode = "langchain-pending"

    def run(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        targets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        target_names = []
        for item in targets or []:
            name = item.get("name") or item.get("symbol") or item.get("type")
            if name:
                target_names.append(str(name))

        lines = [
            "智能体能力暂未接入。当前后端已完成数据库接口对齐，并预留 LangChain Agent 接入位。",
            "后续会在这里补齐提示词编排、工具调用、记忆管理和执行链路。",
        ]
        if target_names:
            lines.insert(1, f"本次请求携带的分析目标：{'、'.join(target_names)}。")
        if message.strip():
            lines.append("当前阶段你仍可验证公司、行情、诊断、风险和资讯等数据库接口。")

        return {
            "answer": "\n".join(lines),
            "framework": self.framework,
            "agent_mode": self.agent_mode,
            "targets": target_names,
        }
