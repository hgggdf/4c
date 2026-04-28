"""蝴蝶效应分析路由。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.router.dependencies import get_container
from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.butterfly_service import ButterflyRequest, ButterflyHistoryRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/butterfly", tags=["butterfly"])


class ButterflyAnalysisModel(BaseModel):
    event: str = Field(..., min_length=1)
    industry_filter: list[str] = Field(default_factory=list)
    max_companies: int = Field(default=30, ge=1, le=100)


class ButterflyHistoryModel(BaseModel):
    days: int = Field(default=90, ge=1, le=365)
    event_type: str | None = None
    severity: str | None = None
    keyword: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/analyze")
def analyze(payload: ButterflyAnalysisModel, container: ServiceContainer = Depends(get_container)):
    req = ButterflyRequest(
        event=payload.event,
        industry_filter=payload.industry_filter,
        max_companies=payload.max_companies,
    )

    def event_generator():
        try:
            for event in container.butterfly.analyze_stream(req):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("butterfly analyze error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/history")
def list_history(payload: ButterflyHistoryModel, container: ServiceContainer = Depends(get_container)):
    return service_result_response(
        container.butterfly.list_history(build_request(ButterflyHistoryRequest, payload))
    )


__all__ = ["router"]
