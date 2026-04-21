"""公司写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.company import (
	BatchUpsertIndustriesModel,
	ReplaceCompanyIndustriesModel,
	UpsertCompanyMasterModel,
	UpsertCompanyProfileModel,
	UpsertWatchlistModel,
)

from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import (
	BatchUpsertIndustriesRequest,
	ReplaceCompanyIndustriesRequest,
	UpsertCompanyMasterRequest,
	UpsertCompanyProfileRequest,
	UpsertWatchlistRequest,
)

router = APIRouter(prefix="/api/company-write", tags=["company-write"])


@router.post("/upsert-master")
def upsert_company_master(payload: UpsertCompanyMasterModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.upsert_company_master(build_request(UpsertCompanyMasterRequest, payload)))


@router.post("/batch-upsert-master")
def batch_upsert_company_master(payload: BatchUpsertIndustriesModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.batch_upsert_company_master(build_request(BatchUpsertIndustriesRequest, payload)))


@router.post("/upsert-profile")
def upsert_company_profile(payload: UpsertCompanyProfileModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.upsert_company_profile(build_request(UpsertCompanyProfileRequest, payload)))


@router.post("/batch-upsert-industries")
def batch_upsert_industries(payload: BatchUpsertIndustriesModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.batch_upsert_industries(build_request(BatchUpsertIndustriesRequest, payload)))


@router.post("/replace-company-industries")
def replace_company_industries(payload: ReplaceCompanyIndustriesModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.replace_company_industries(build_request(ReplaceCompanyIndustriesRequest, payload)))


@router.post("/upsert-watchlist")
def upsert_watchlist(payload: UpsertWatchlistModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company_write.upsert_watchlist(build_request(UpsertWatchlistRequest, payload)))


__all__ = ["router"]