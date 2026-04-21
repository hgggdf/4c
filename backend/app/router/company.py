"""公司查询路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.company import TextResolveModel
from app.router.utils import service_result_response
from app.service import ServiceContainer

router = APIRouter(prefix="/api/company", tags=["company"])


@router.get("/basic/{stock_code}")
def get_company_basic_info(stock_code: str, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.get_company_basic_info(stock_code))


@router.get("/profile/{stock_code}")
def get_company_profile(stock_code: str, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.get_company_profile(stock_code))


@router.get("/industries/{stock_code}")
def get_company_industries(stock_code: str, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.get_company_industries(stock_code))


@router.get("/overview/{stock_code}")
def get_company_overview(stock_code: str, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.get_company_overview(stock_code))


@router.get("/exists/{stock_code}")
def ensure_company_exists(stock_code: str, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.ensure_company_exists(stock_code))


@router.post("/resolve")
def resolve_company(payload: TextResolveModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.company.resolve_company(payload.text))


__all__ = ["router"]