"""维护路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.maintenance import (
	ArchiveHotDataModel,
	InvalidateStockCacheModel,
	RebuildAnnouncementSummaryModel,
	RebuildDrugPipelineSummaryModel,
	RebuildFinancialMetricSummaryModel,
	RebuildIndustryNewsSummaryModel,
)

from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import (
	ArchiveHotDataRequest,
	InvalidateStockCacheRequest,
	RebuildAnnouncementSummaryRequest,
	RebuildDrugPipelineSummaryRequest,
	RebuildFinancialMetricSummaryRequest,
	RebuildIndustryNewsSummaryRequest,
)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.post("/archive-hot-data")
def archive_hot_data(payload: ArchiveHotDataModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.archive_hot_data(build_request(ArchiveHotDataRequest, payload)))


@router.post("/rebuild-financial-metric-summary-yearly")
def rebuild_financial_metric_summary_yearly(payload: RebuildFinancialMetricSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.rebuild_financial_metric_summary_yearly(build_request(RebuildFinancialMetricSummaryRequest, payload)))


@router.post("/rebuild-announcement-summary-monthly")
def rebuild_announcement_summary_monthly(payload: RebuildAnnouncementSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.rebuild_announcement_summary_monthly(build_request(RebuildAnnouncementSummaryRequest, payload)))


@router.post("/rebuild-drug-pipeline-summary-yearly")
def rebuild_drug_pipeline_summary_yearly(payload: RebuildDrugPipelineSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.rebuild_drug_pipeline_summary_yearly(build_request(RebuildDrugPipelineSummaryRequest, payload)))


@router.post("/rebuild-industry-news-summary-monthly")
def rebuild_industry_news_summary_monthly(payload: RebuildIndustryNewsSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.rebuild_industry_news_summary_monthly(build_request(RebuildIndustryNewsSummaryRequest, payload)))


@router.post("/invalidate-stock-related-caches")
def invalidate_stock_related_caches(payload: InvalidateStockCacheModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.maintenance.invalidate_stock_related_caches(build_request(InvalidateStockCacheRequest, payload)))


__all__ = ["router"]