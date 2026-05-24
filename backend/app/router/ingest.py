"""组合写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.ingest import (
	IngestAnnouncementPackageModel,
	IngestCompanyPackageModel,
	IngestFinancialPackageModel,
	IngestNewsPackageModel,
)

from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import (
	IngestAnnouncementPackageRequest,
	IngestCompanyPackageRequest,
	IngestFinancialPackageRequest,
	IngestNewsPackageRequest,
)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/company-package")
def ingest_company_package(payload: IngestCompanyPackageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.ingest.ingest_company_package(build_request(IngestCompanyPackageRequest, payload)))


@router.post("/financial-package")
def ingest_financial_package(payload: IngestFinancialPackageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.ingest.ingest_financial_package(build_request(IngestFinancialPackageRequest, payload)))


@router.post("/announcement-package")
def ingest_announcement_package(payload: IngestAnnouncementPackageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.ingest.ingest_announcement_package(build_request(IngestAnnouncementPackageRequest, payload)))


@router.post("/news-package")
def ingest_news_package(payload: IngestNewsPackageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.ingest.ingest_news_package(build_request(IngestNewsPackageRequest, payload)))


__all__ = ["router"]