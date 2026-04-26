"""ORM models package（v3）。

v3 正式表（16张）：
  app_user, watchlist, chat_session, chat_history,
  industry_master, company,
  financial_hot, financial_archive,
  announcement_hot, announcement_archive,
  research_report_hot, research_report_archive,
  macro_indicator,
  news_hot, news_archive,
  vector_document_index, data_job_log
  + staging_import（入库中转）
"""

from .user import User, ChatSession, ChatMessage, Watchlist
from .company import (
    IndustryMaster,
    Company,
    CompanyMaster,
    CompanyProfile,
    CompanyIndustryMap,
)
from .financial_hot import (
    FinancialHot,
    FinancialArchive,
    IncomeStatementHot,
    BalanceSheetHot,
    CashflowStatementHot,
    FinancialMetricHot,
    FinancialNotesHot,
    BusinessSegmentHot,
    StockDailyHot,
    IncomeStatementArchive,
    BalanceSheetArchive,
    CashflowStatementArchive,
    FinancialMetricArchive,
    FinancialNotesArchive,
    BusinessSegmentArchive,
    StockDailyArchive,
)
from .announcement_hot import (
    AnnouncementHot,
    AnnouncementArchive,
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    AnnouncementRawArchive,
    AnnouncementStructuredArchive,
    DrugApprovalHot,
    ClinicalTrialEventHot,
    CentralizedProcurementEventHot,
    RegulatoryRiskEventHot,
    DrugApprovalArchive,
    ClinicalTrialEventArchive,
    CentralizedProcurementEventArchive,
    RegulatoryRiskEventArchive,
)
from .research_report_hot import ResearchReportHot, ResearchReportArchive
from .macro_hot import MacroIndicator, MacroIndicatorHot, MacroIndicatorArchive
from .news_hot import (
    NewsHot,
    NewsArchive,
    NewsRawHot,
    NewsStructuredHot,
    NewsRawArchive,
    NewsStructuredArchive,
    NewsIndustryMapHot,
    NewsCompanyMapHot,
    IndustryImpactEventHot,
    NewsIndustryMapArchive,
    NewsCompanyMapArchive,
    IndustryImpactEventArchive,
)
from .vector_and_job import VectorDocumentIndex, DataJobLog, StagingImport

__all__ = [
    "User", "ChatSession", "ChatMessage", "Watchlist",
    "IndustryMaster", "Company", "CompanyMaster", "CompanyProfile", "CompanyIndustryMap",
    "FinancialHot", "FinancialArchive",
    "IncomeStatementHot", "BalanceSheetHot", "CashflowStatementHot",
    "FinancialMetricHot", "FinancialNotesHot", "BusinessSegmentHot", "StockDailyHot",
    "IncomeStatementArchive", "BalanceSheetArchive", "CashflowStatementArchive",
    "FinancialMetricArchive", "FinancialNotesArchive", "BusinessSegmentArchive", "StockDailyArchive",
    "AnnouncementHot", "AnnouncementArchive",
    "AnnouncementRawHot", "AnnouncementStructuredHot",
    "AnnouncementRawArchive", "AnnouncementStructuredArchive",
    "DrugApprovalHot", "ClinicalTrialEventHot", "CentralizedProcurementEventHot", "RegulatoryRiskEventHot",
    "DrugApprovalArchive", "ClinicalTrialEventArchive", "CentralizedProcurementEventArchive", "RegulatoryRiskEventArchive",
    "ResearchReportHot", "ResearchReportArchive",
    "MacroIndicator", "MacroIndicatorHot", "MacroIndicatorArchive",
    "NewsHot", "NewsArchive",
    "NewsRawHot", "NewsStructuredHot", "NewsRawArchive", "NewsStructuredArchive",
    "NewsIndustryMapHot", "NewsCompanyMapHot", "IndustryImpactEventHot",
    "NewsIndustryMapArchive", "NewsCompanyMapArchive", "IndustryImpactEventArchive",
    "VectorDocumentIndex", "DataJobLog", "StagingImport",
]
