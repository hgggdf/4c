from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    user_question: str
    session_id: int | None = None
    user_id: int | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    targets: list[dict[str, Any]] = field(default_factory=list)
    current_stock_code: str | None = None

    selected_mode: str | None = None
    frontend_context: dict[str, Any] | None = None
    followup_from: str | None = None
    preference_hint: dict[str, Any] | None = None

    resolved_mode: str | None = None
    company_entity: dict[str, Any] | None = None
    drug_entity: dict[str, Any] | None = None
    industry_entity: dict[str, Any] | None = None
    time_range: dict[str, Any] | None = None
    preference_profile: dict[str, Any] | None = None
    freshness_strategy: str | None = None
    tool_plan: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    retrieval_trace: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)

    medical_analysis: dict[str, Any] | None = None
    score_result: dict[str, Any] | None = None
    key_metrics: list[dict[str, Any]] = field(default_factory=list)
    chart_payload: list[dict[str, Any]] = field(default_factory=list)
    evidence_list: list[dict[str, Any]] = field(default_factory=list)

    answer: str | None = None
    summary: str | None = None
    key_points: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    suggestion: str | None = None
    chart_desc: str | None = None
    report_markdown: str | None = None
    agent_mode: str | None = None
    framework: str | None = None
    warnings: list[dict[str, Any] | str] = field(default_factory=list)

    def add_warning(self, warning_type: str, message: str, detail: dict[str, Any] | None = None) -> None:
        self.warnings.append({
            "type": warning_type,
            "message": message,
            "detail": detail or {},
        })

    def to_agent_result(self) -> dict[str, Any]:
        selected_mode = self.resolved_mode or self.selected_mode
        return {
            "answer": self.answer or "",
            "suggestion": self.suggestion,
            "chart_desc": self.chart_desc,
            "report_markdown": self.report_markdown,
            "agent_mode": self.agent_mode,
            "framework": self.framework,
            "summary": self.summary,
            "selected_mode": selected_mode,
            "key_points": list(self.key_points) if self.key_points else [],
            "key_metrics": list(self.key_metrics) if self.key_metrics else [],
            "score_result": self.score_result,
            "chart_payload": list(self.chart_payload) if self.chart_payload else [],
            "evidence_list": list(self.evidence_list) if self.evidence_list else [],
            "retrieval_trace": list(self.retrieval_trace) if self.retrieval_trace else [],
            "tool_trace": list(self.tool_trace) if self.tool_trace else [],
            "follow_up_questions": list(self.follow_up_questions) if self.follow_up_questions else [],
            "preference_profile": self.preference_profile,
            "warnings": list(self.warnings) if self.warnings else [],
        }
