"""缓存管理路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.cache import (
	CacheGetHotDataModel,
	CacheGetSessionContextModel,
	CacheInvalidateModel,
	CacheQueryModel,
	CacheSetHotDataModel,
	CacheSetQueryModel,
	CacheSetSessionContextModel,
)

from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import (
	CacheGetHotDataRequest,
	CacheGetSessionContextRequest,
	CacheInvalidateRequest,
	CacheQueryRequest,
	CacheSetHotDataRequest,
	CacheSetQueryRequest,
	CacheSetSessionContextRequest,
)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.post("/query/get")
def get_query_cache(payload: CacheQueryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.get_query_cache(build_request(CacheQueryRequest, payload)))


@router.post("/query/set")
def set_query_cache(payload: CacheSetQueryModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.set_query_cache(build_request(CacheSetQueryRequest, payload)))


@router.post("/session-context/get")
def get_session_context(payload: CacheGetSessionContextModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.get_session_context(build_request(CacheGetSessionContextRequest, payload)))


@router.post("/session-context/set")
def set_session_context(payload: CacheSetSessionContextModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.set_session_context(build_request(CacheSetSessionContextRequest, payload)))


@router.post("/hot-data/get")
def get_hot_data(payload: CacheGetHotDataModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.get_hot_data(build_request(CacheGetHotDataRequest, payload)))


@router.post("/hot-data/set")
def set_hot_data(payload: CacheSetHotDataModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.set_hot_data(build_request(CacheSetHotDataRequest, payload)))


@router.post("/invalidate")
def invalidate(payload: CacheInvalidateModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.cache.invalidate(build_request(CacheInvalidateRequest, payload)))


__all__ = ["router"]