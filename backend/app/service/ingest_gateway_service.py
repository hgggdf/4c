from __future__ import annotations

from .announcement_write_service import AnnouncementWriteService
from .base import BaseService
from .company_write_service import CompanyWriteService
from .financial_write_service import FinancialWriteService
from .macro_write_service import MacroWriteService
from .news_write_service import NewsWriteService
from .write_requests import (
    BatchItemsRequest,
    BatchUpsertFinancialRequest,
    BatchUpsertIndustriesRequest,
    IngestAnnouncementPackageRequest,
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    IngestNewsPackageRequest,
    ReplaceCompanyIndustriesRequest,
    ReplaceNewsCompanyMapRequest,
    ReplaceNewsIndustryMapRequest,
    UpsertCompanyMasterRequest,
    UpsertCompanyProfileRequest,
)


class IngestGatewayService(BaseService):
    def __init__(self, *, ctx, company_write: CompanyWriteService, financial_write: FinancialWriteService, announcement_write: AnnouncementWriteService, macro_write: MacroWriteService, news_write: NewsWriteService) -> None:
        super().__init__(ctx=ctx)
        self.company_write = company_write
        self.financial_write = financial_write
        self.announcement_write = announcement_write
        self.macro_write = macro_write
        self.news_write = news_write

    def ingest_company_package(self, req: IngestCompanyPackageRequest):
        return self._run(lambda: self._ingest_company_package(req), trace_id=req.trace_id)

    def ingest_financial_package(self, req: IngestFinancialPackageRequest):
        return self._run(lambda: self._ingest_financial_package(req), trace_id=req.trace_id)

    def ingest_announcement_package(self, req: IngestAnnouncementPackageRequest):
        return self._run(lambda: self._ingest_announcement_package(req), trace_id=req.trace_id)

    def ingest_news_package(self, req: IngestNewsPackageRequest):
        return self._run(lambda: self._ingest_news_package(req), trace_id=req.trace_id)

    def _ingest_company_package(self, req: IngestCompanyPackageRequest) -> dict:
        result: dict = {}
        if req.company_master:
            master = self.company_write.upsert_company_master(UpsertCompanyMasterRequest(**req.company_master))
            if not master.success:
                raise ValueError(master.message)
            result["company_master"] = master.data
        if req.company_profile:
            profile = self.company_write.upsert_company_profile(UpsertCompanyProfileRequest(sync_vector_index=True, **req.company_profile))
            if not profile.success:
                raise ValueError(profile.message)
            result["company_profile"] = profile.data
        if req.industries:
            industries = self.company_write.batch_upsert_industries(BatchUpsertIndustriesRequest(items=req.industries))
            if not industries.success:
                raise ValueError(industries.message)
            result["industries"] = industries.data
        if req.company_industries and req.company_master:
            mappings = self.company_write.replace_company_industries(
                ReplaceCompanyIndustriesRequest(stock_code=req.company_master["stock_code"], items=req.company_industries)
            )
            if not mappings.success:
                raise ValueError(mappings.message)
            result["company_industries"] = mappings.data
        return result

    def _ingest_financial_package(self, req: IngestFinancialPackageRequest) -> dict:
        result: dict = {}
        if req.income_statements:
            result["income_statements"] = self.financial_write.batch_upsert_income_statements(BatchUpsertFinancialRequest(items=req.income_statements)).data
        if req.balance_sheets:
            result["balance_sheets"] = self.financial_write.batch_upsert_balance_sheets(BatchUpsertFinancialRequest(items=req.balance_sheets)).data
        if req.cashflow_statements:
            result["cashflow_statements"] = self.financial_write.batch_upsert_cashflow_statements(BatchUpsertFinancialRequest(items=req.cashflow_statements)).data
        if req.financial_metrics:
            result["financial_metrics"] = self.financial_write.batch_upsert_financial_metrics(BatchUpsertFinancialRequest(items=req.financial_metrics)).data
        if req.financial_notes:
            result["financial_notes"] = self.financial_write.batch_upsert_financial_notes(BatchUpsertFinancialRequest(items=req.financial_notes, sync_vector_index=req.sync_vector_index)).data
        if req.business_segments:
            result["business_segments"] = self.financial_write.batch_upsert_business_segments(BatchUpsertFinancialRequest(items=req.business_segments)).data
        if req.stock_daily:
            result["stock_daily"] = self.financial_write.batch_upsert_stock_daily(BatchUpsertFinancialRequest(items=req.stock_daily)).data
        return result

    def _ingest_announcement_package(self, req: IngestAnnouncementPackageRequest) -> dict:
        result: dict = {}
        if req.raw_announcements:
            result["raw_announcements"] = self.announcement_write.batch_upsert_raw_announcements(BatchItemsRequest(items=req.raw_announcements, sync_vector_index=req.sync_vector_index)).data
        if req.structured_announcements:
            result["structured_announcements"] = self.announcement_write.batch_upsert_structured_announcements(BatchItemsRequest(items=req.structured_announcements)).data
        if req.drug_approvals:
            result["drug_approvals"] = self.announcement_write.batch_upsert_drug_approvals(BatchItemsRequest(items=req.drug_approvals)).data
        if req.clinical_trials:
            result["clinical_trials"] = self.announcement_write.batch_upsert_clinical_trials(BatchItemsRequest(items=req.clinical_trials)).data
        if req.procurement_events:
            result["procurement_events"] = self.announcement_write.batch_upsert_procurement_events(BatchItemsRequest(items=req.procurement_events)).data
        if req.regulatory_risks:
            result["regulatory_risks"] = self.announcement_write.batch_upsert_regulatory_risks(BatchItemsRequest(items=req.regulatory_risks)).data
        return result

    def _ingest_news_package(self, req: IngestNewsPackageRequest) -> dict:
        result: dict = {}
        if req.macro_indicators:
            result["macro_indicators"] = self.macro_write.batch_upsert_macro_indicators(BatchItemsRequest(items=req.macro_indicators)).data
        if req.news_raw:
            result["news_raw"] = self.news_write.batch_upsert_news_raw(BatchItemsRequest(items=req.news_raw, sync_vector_index=req.sync_vector_index)).data
        if req.news_structured:
            result["news_structured"] = self.news_write.batch_upsert_news_structured(BatchItemsRequest(items=req.news_structured)).data
        if req.news_industry_maps:
            mapping_results = {}
            for news_id, items in req.news_industry_maps.items():
                mapping_results[str(news_id)] = self.news_write.replace_news_industry_map(ReplaceNewsIndustryMapRequest(news_id=int(news_id), items=items)).data
            result["news_industry_maps"] = mapping_results
        if req.news_company_maps:
            mapping_results = {}
            for news_id, items in req.news_company_maps.items():
                mapping_results[str(news_id)] = self.news_write.replace_news_company_map(ReplaceNewsCompanyMapRequest(news_id=int(news_id), items=items)).data
            result["news_company_maps"] = mapping_results
        if req.industry_impact_events:
            result["industry_impact_events"] = self.news_write.batch_upsert_industry_impact_events(BatchItemsRequest(items=req.industry_impact_events)).data
        return result
