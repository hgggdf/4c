"""新闻查询路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.news import ImpactSummaryModel, IndustryDaysModel, NewsRawModel, NewsStructuredModel, StockCodeDaysModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import ImpactSummaryRequest, IndustryDaysRequest, NewsRawRequest, NewsStructuredRequest, StockCodeDaysRequest

router = APIRouter(prefix="/api/news", tags=["news"])


@router.post("/raw")
def get_news_raw(payload: NewsRawModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_news_raw(build_request(NewsRawRequest, payload)))


@router.post("/by-company")
def get_news_by_company(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_news_by_company(build_request(StockCodeDaysRequest, payload)))


@router.post("/by-industry")
def get_news_by_industry(payload: IndustryDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_news_by_industry(build_request(IndustryDaysRequest, payload)))


@router.post("/structured")
def get_news_structured(payload: NewsStructuredModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_news_structured(build_request(NewsStructuredRequest, payload)))


@router.post("/company-impact")
def get_company_news_impact(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_company_news_impact(build_request(StockCodeDaysRequest, payload)))


@router.post("/industry-impact")
def get_industry_news_impact(payload: IndustryDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_industry_news_impact(build_request(IndustryDaysRequest, payload)))


@router.post("/impact-summary")
def get_news_impact_summary(payload: ImpactSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_news_impact_summary(build_request(ImpactSummaryRequest, payload)))


@router.post("/reports-by-industry")
def get_reports_by_industry(payload: IndustryDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.news.get_reports_by_industry(build_request(IndustryDaysRequest, payload)))


__all__ = ["router"]