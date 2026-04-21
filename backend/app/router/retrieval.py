"""检索路由。"""

from fastapi import APIRouter, Depends

from app.router.dependencies import get_container
from app.router.schemas.retrieval import RebuildEmbeddingsModel, SearchModel
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import RebuildEmbeddingsRequest, SearchRequest

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/announcements")
def search_announcements(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_announcements(build_request(SearchRequest, payload)))


@router.post("/financial-notes")
def search_financial_notes(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_financial_notes(build_request(SearchRequest, payload)))


@router.post("/news")
def search_news(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_news(build_request(SearchRequest, payload)))


@router.post("/reports")
def search_reports(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_reports(build_request(SearchRequest, payload)))


@router.post("/policies")
def search_policies(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_policies(build_request(SearchRequest, payload)))


@router.post("/text-evidence")
def search_text_evidence(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_text_evidence(build_request(SearchRequest, payload)))


@router.post("/announcement-evidence")
def search_announcement_evidence(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_announcement_evidence(build_request(SearchRequest, payload)))


@router.post("/financial-note-evidence")
def search_financial_note_evidence(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_financial_note_evidence(build_request(SearchRequest, payload)))


@router.post("/news-evidence")
def search_news_evidence(payload: SearchModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.search_news_evidence(build_request(SearchRequest, payload)))


@router.post("/rebuild-embeddings")
def rebuild_document_embeddings(payload: RebuildEmbeddingsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.rebuild_document_embeddings(build_request(RebuildEmbeddingsRequest, payload)))


@router.post("/delete-embeddings")
def delete_document_embeddings(payload: RebuildEmbeddingsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.retrieval.delete_document_embeddings(build_request(RebuildEmbeddingsRequest, payload)))


__all__ = ["router"]