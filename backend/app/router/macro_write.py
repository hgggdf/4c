"""宏观写入路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.macro import BatchItemsModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.write_requests import BatchItemsRequest

router = APIRouter(prefix="/api/macro-write", tags=["macro-write"])


@router.post("/macro-indicators")
def batch_upsert_macro_indicators(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.macro_write.batch_upsert_macro_indicators(build_request(BatchItemsRequest, payload)))


@router.post("/delete-macro-indicators")
def batch_delete_macro_indicators(payload: BatchItemsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.macro_write.batch_delete_macro_indicators(build_request(BatchItemsRequest, payload)))


__all__ = ["router"]