"""LangChain 工具注册占位。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentToolSpec:
    name: str
    description: str


class LangChainToolRegistry:
    """后续供 LangChain Agent 装配工具使用的轻量注册表。"""

    def __init__(self) -> None:
        self._tools: list[AgentToolSpec] = []

    def register(self, name: str, description: str) -> AgentToolSpec:
        tool = AgentToolSpec(name=name, description=description)
        self._tools.append(tool)
        return tool

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools
        ]
