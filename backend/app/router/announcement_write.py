"""公告写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.announcement import BatchItemsModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import BatchItemsRequest

router = APIRouter(prefix="/api/announcement-write", tags=["announcement-write"])


@router.post("/raw-announcements")
def batch_upsert_raw_announcements(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_raw_announcements(build_request(BatchItemsRequest, payload)))


@router.post("/delete-raw-announcements")
def batch_delete_raw_announcements(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_raw_announcements(build_request(BatchItemsRequest, payload)))


@router.post("/structured-announcements")
def batch_upsert_structured_announcements(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_structured_announcements(build_request(BatchItemsRequest, payload)))


@router.post("/delete-structured-announcements")
def batch_delete_structured_announcements(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_structured_announcements(build_request(BatchItemsRequest, payload)))


@router.post("/drug-approvals")
def batch_upsert_drug_approvals(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_drug_approvals(build_request(BatchItemsRequest, payload)))


@router.post("/delete-drug-approvals")
def batch_delete_drug_approvals(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_drug_approvals(build_request(BatchItemsRequest, payload)))


@router.post("/clinical-trials")
def batch_upsert_clinical_trials(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_clinical_trials(build_request(BatchItemsRequest, payload)))


@router.post("/delete-clinical-trials")
def batch_delete_clinical_trials(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_clinical_trials(build_request(BatchItemsRequest, payload)))


@router.post("/procurement-events")
def batch_upsert_procurement_events(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_procurement_events(build_request(BatchItemsRequest, payload)))


@router.post("/delete-procurement-events")
def batch_delete_procurement_events(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_procurement_events(build_request(BatchItemsRequest, payload)))


@router.post("/regulatory-risks")
def batch_upsert_regulatory_risks(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_upsert_regulatory_risks(build_request(BatchItemsRequest, payload)))


@router.post("/delete-regulatory-risks")
def batch_delete_regulatory_risks(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.announcement_write.batch_delete_regulatory_risks(build_request(BatchItemsRequest, payload)))


__all__ = ["router"]