"""新闻写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.news import BatchItemsModel, ReplaceNewsCompanyMapModel, ReplaceNewsIndustryMapModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import BatchItemsRequest, ReplaceNewsCompanyMapRequest, ReplaceNewsIndustryMapRequest

router = APIRouter(prefix="/api/news-write", tags=["news-write"])


@router.post("/news-raw")
def batch_upsert_news_raw(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_upsert_news_raw(build_request(BatchItemsRequest, payload)))


@router.post("/delete-news-raw")
def batch_delete_news_raw(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_delete_news_raw(build_request(BatchItemsRequest, payload)))


@router.post("/news-structured")
def batch_upsert_news_structured(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_upsert_news_structured(build_request(BatchItemsRequest, payload)))


@router.post("/delete-news-structured")
def batch_delete_news_structured(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_delete_news_structured(build_request(BatchItemsRequest, payload)))


@router.post("/replace-industry-map")
def replace_news_industry_map(payload: ReplaceNewsIndustryMapModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.replace_news_industry_map(build_request(ReplaceNewsIndustryMapRequest, payload)))


@router.post("/replace-company-map")
def replace_news_company_map(payload: ReplaceNewsCompanyMapModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.replace_news_company_map(build_request(ReplaceNewsCompanyMapRequest, payload)))


@router.post("/industry-impact-events")
def batch_upsert_industry_impact_events(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_upsert_industry_impact_events(build_request(BatchItemsRequest, payload)))


@router.post("/delete-industry-impact-events")
def batch_delete_industry_impact_events(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news_write.batch_delete_industry_impact_events(build_request(BatchItemsRequest, payload)))


__all__ = ["router"]