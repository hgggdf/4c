"""宏观查询路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.macro import MacroIndicatorModel, MacroListModel, MacroSummaryModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import MacroIndicatorRequest, MacroListRequest, MacroSummaryRequest

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.post("/indicator")
def get_macro_indicator(payload: MacroIndicatorModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.macro.get_macro_indicator(build_request(MacroIndicatorRequest, payload)))


@router.post("/list")
def list_macro_indicators(payload: MacroListModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.macro.list_macro_indicators(build_request(MacroListRequest, payload)))


@router.post("/summary")
def get_macro_summary(payload: MacroSummaryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.macro.get_macro_summary(build_request(MacroSummaryRequest, payload)))


__all__ = ["router"]