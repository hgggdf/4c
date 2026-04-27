from __future__ import annotations

from dataclasses import dataclass

from .announcement_service import AnnouncementService
from .announcement_write_service import AnnouncementWriteService
from .cache_service import CacheService
from .chat_service import ChatService
from .company_service import CompanyService
from .company_write_service import CompanyWriteService
from .context import ServiceContext, build_default_context
from .financial_service import FinancialService
from .financial_write_service import FinancialWriteService
from .ingest_gateway_service import IngestGatewayService
from .macro_service import MacroService
from .macro_write_service import MacroWriteService
from .maintenance_service import MaintenanceService
from .news_service import NewsService
from .news_write_service import NewsWriteService
from .research_report_write_service import ResearchReportWriteService
from .retrieval_service import RetrievalService


@dataclass(slots=True)
class ServiceContainer:
    ctx: ServiceContext
    company: CompanyService
    financial: FinancialService
    announcement: AnnouncementService
    news: NewsService
    macro: MacroService
    retrieval: RetrievalService
    chat: ChatService
    cache: CacheService
    company_write: CompanyWriteService
    financial_write: FinancialWriteService
    announcement_write: AnnouncementWriteService
    macro_write: MacroWriteService
    news_write: NewsWriteService
    research_report_write: ResearchReportWriteService
    maintenance: MaintenanceService
    ingest: IngestGatewayService

    @staticmethod
    def build_default() -> "ServiceContainer":
        ctx = build_default_context()
        company = CompanyService(ctx=ctx)
        retrieval = RetrievalService(ctx=ctx, company_service=company)
        cache = CacheService(ctx=ctx)
        company_write = CompanyWriteService(ctx=ctx)
        financial_write = FinancialWriteService(ctx=ctx)
        announcement_write = AnnouncementWriteService(ctx=ctx)
        macro_write = MacroWriteService(ctx=ctx)
        news_write = NewsWriteService(ctx=ctx)
        research_report_write = ResearchReportWriteService(ctx=ctx)
        maintenance = MaintenanceService(ctx=ctx)
        return ServiceContainer(
            ctx=ctx,
            company=company,
            financial=FinancialService(ctx=ctx, company_service=company),
            announcement=AnnouncementService(ctx=ctx, company_service=company),
            news=NewsService(ctx=ctx, company_service=company, retrieval_service=retrieval),
            macro=MacroService(ctx=ctx),
            retrieval=retrieval,
            chat=ChatService(ctx=ctx, company_service=company, cache_service=cache),
            cache=cache,
            company_write=company_write,
            financial_write=financial_write,
            announcement_write=announcement_write,
            macro_write=macro_write,
            news_write=news_write,
            research_report_write=research_report_write,
            maintenance=maintenance,
            ingest=IngestGatewayService(
                ctx=ctx,
                company_write=company_write,
                financial_write=financial_write,
                announcement_write=announcement_write,
                macro_write=macro_write,
                news_write=news_write,
            ),
        )
