"""公告查询路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.announcement import StockCodeDaysModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import StockCodeDaysRequest

router = APIRouter(prefix="/api/announcement", tags=["announcement"])


@router.post("/raw")
def get_raw_announcements(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_raw_announcements(build_request(StockCodeDaysRequest, payload)))


@router.post("/structured")
def get_structured_announcements(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_structured_announcements(build_request(StockCodeDaysRequest, payload)))


@router.post("/drug-approvals")
def get_drug_approvals(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_drug_approvals(build_request(StockCodeDaysRequest, payload)))


@router.post("/clinical-trials")
def get_clinical_trials(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_clinical_trials(build_request(StockCodeDaysRequest, payload)))


@router.post("/procurement-events")
def get_procurement_events(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_procurement_events(build_request(StockCodeDaysRequest, payload)))


@router.post("/regulatory-risks")
def get_regulatory_risks(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_regulatory_risks(build_request(StockCodeDaysRequest, payload)))


@router.post("/company-event-summary")
def get_company_event_summary(payload: StockCodeDaysModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement.get_company_event_summary(build_request(StockCodeDaysRequest, payload)))


__all__ = ["router"]