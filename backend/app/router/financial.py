"""财务查询路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.financial import FinancialMetricsModel, FinancialSummaryModel, StockCodeLimitModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import FinancialMetricsRequest, FinancialSummaryRequest, StockCodeLimitRequest

router = APIRouter(prefix="/api/financial", tags=["financial"])


@router.post("/income-statements")
def get_income_statements(payload: StockCodeLimitModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_income_statements(build_request(StockCodeLimitRequest, payload)))


@router.post("/balance-sheets")
def get_balance_sheets(payload: StockCodeLimitModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_balance_sheets(build_request(StockCodeLimitRequest, payload)))


@router.post("/cashflow-statements")
def get_cashflow_statements(payload: StockCodeLimitModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_cashflow_statements(build_request(StockCodeLimitRequest, payload)))


@router.post("/metrics")
def get_financial_metrics(payload: FinancialMetricsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_financial_metrics(build_request(FinancialMetricsRequest, payload)))


@router.post("/business-segments")
def get_business_segments(payload: StockCodeLimitModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_business_segments(build_request(StockCodeLimitRequest, payload)))


@router.post("/summary")
def get_financial_summary(payload: FinancialSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.financial.get_financial_summary(build_request(FinancialSummaryRequest, payload)))


__all__ = ["router"]