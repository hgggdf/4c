"""智能体能力包。"""

from .integration import GLMMinimalAgent, LangChainAgentStub
from .llm_clients import GLMClient
from .prompts import SYSTEM_PROMPT, PromptTemplates, build_chat_messages
from .tools import (
    AgentToolSpec,
    LangChainToolRegistry,
    get_balance_sheets,
    get_business_segments,
    get_cashflow_statements,
    get_clinical_trials,
    get_company_basic_info,
    get_company_event_summary,
    get_company_news_impact,
    get_company_overview,
    get_company_profile,
    get_drug_approvals,
    get_financial_metrics,
    get_financial_summary,
    get_income_statements,
    get_industry_news_impact,
    get_macro_indicator,
    get_macro_summary,
    get_news_by_company,
    get_news_by_industry,
    get_news_raw,
    get_procurement_events,
    get_raw_announcements,
    get_regulatory_risks,
    get_structured_announcements,
    list_macro_indicators,
    resolve_company_from_text,
    search_company_evidence,
    search_documents,
    search_news_evidence,
)

__all__ = [
    # Agent implementations
    "GLMMinimalAgent",
    "LangChainAgentStub",
    # LLM clients
    "GLMClient",
    # Prompts
    "SYSTEM_PROMPT",
    "PromptTemplates",
    "build_chat_messages",
    # Tool registry
    "AgentToolSpec",
    "LangChainToolRegistry",
    # Company tools
    "get_company_basic_info",
    "get_company_profile",
    "get_company_overview",
    "resolve_company_from_text",
    # Financial tools
    "get_income_statements",
    "get_balance_sheets",
    "get_cashflow_statements",
    "get_financial_metrics",
    "get_business_segments",
    "get_financial_summary",
    # Announcement tools
    "get_raw_announcements",
    "get_structured_announcements",
    "get_drug_approvals",
    "get_clinical_trials",
    "get_procurement_events",
    "get_regulatory_risks",
    "get_company_event_summary",
    # News tools
    "get_news_raw",
    "get_news_by_company",
    "get_news_by_industry",
    "get_company_news_impact",
    "get_industry_news_impact",
    # Macro tools
    "get_macro_indicator",
    "list_macro_indicators",
    "get_macro_summary",
    # Retrieval tools
    "search_documents",
    "search_company_evidence",
    "search_news_evidence",
]
