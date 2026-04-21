"""财务写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.financial import BatchUpsertFinancialModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import BatchUpsertFinancialRequest

router = APIRouter(prefix="/api/financial-write", tags=["financial-write"])


@router.post("/income-statements")
def batch_upsert_income_statements(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_income_statements(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/balance-sheets")
def batch_upsert_balance_sheets(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_balance_sheets(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/cashflow-statements")
def batch_upsert_cashflow_statements(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_cashflow_statements(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/financial-metrics")
def batch_upsert_financial_metrics(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_financial_metrics(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/financial-notes")
def batch_upsert_financial_notes(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_financial_notes(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/business-segments")
def batch_upsert_business_segments(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_business_segments(build_request(BatchUpsertFinancialRequest, payload)))


@router.post("/stock-daily")
def batch_upsert_stock_daily(payload: BatchUpsertFinancialModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial_write.batch_upsert_stock_daily(build_request(BatchUpsertFinancialRequest, payload)))


__all__ = ["router"]