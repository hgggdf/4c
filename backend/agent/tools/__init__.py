"""智能体工具包 - 封装所有数据库接口为Agent可调用的工具函数"""

from .announcement_tools import (
    get_clinical_trials,
    get_company_event_summary,
    get_drug_approvals,
    get_procurement_events,
    get_raw_announcements,
    get_regulatory_risks,
    get_structured_announcements,
)
from .company_tools import (
    get_company_basic_info,
    get_company_overview,
    get_company_profile,
    resolve_company_from_text,
)
from .financial_tools import (
    get_balance_sheets,
    get_business_segments,
    get_cashflow_statements,
    get_financial_metrics,
    get_financial_summary,
    get_income_statements,
)
from .macro_tools import (
    get_macro_indicator,
    get_macro_summary,
    list_macro_indicators,
)
from .news_tools import (
    get_company_news_impact,
    get_industry_news_impact,
    get_news_by_company,
    get_news_by_industry,
    get_news_raw,
)
from .registry import AgentToolSpec, LangChainToolRegistry
from .retrieval_tools import (
    search_company_evidence,
    search_documents,
    search_news_evidence,
)

__all__ = [
    # Registry
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