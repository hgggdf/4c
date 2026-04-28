"""兼容现有 chat 主链的最小 GLM 智能体入口。"""

from __future__ import annotations

from typing import Any

from .glm_agent import GLMMinimalAgent


class LangChainAgentStub:
    """保留原导入路径，内部委托给最小 GLM 编排器。"""

    framework = "kimi"
    agent_mode = "kimi-k2.5"

    def __init__(self) -> None:
        self._agent = GLMMinimalAgent()

    def run(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        targets: list[dict[str, Any]] | None = None,
        current_stock_code: str | None = None,
        user_id: int | None = None,
        session_id: int | None = None,
        selected_mode: str | None = None,
        frontend_context: dict[str, Any] | None = None,
        followup_from: str | None = None,
        preference_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._agent.run(
            message,
            history=history,
            targets=targets,
            current_stock_code=current_stock_code,
            user_id=user_id,
            session_id=session_id,
            selected_mode=selected_mode,
            frontend_context=frontend_context,
            followup_from=followup_from,
            preference_hint=preference_hint,
        )
        payload.setdefault("framework", self.framework)
        payload.setdefault("agent_mode", self.agent_mode)
        return payload
