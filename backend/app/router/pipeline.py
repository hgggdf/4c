"""Pipeline and rNPV routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.router.dependencies import get_container
from app.router.schemas.pipeline import (
    PipelineDrugItem,
    PipelineDrugListResponse,
    PipelineDrugUpsertRequest,
    PipelineDrugUpsertResponse,
    RNPVRunCreate,
    RNPVRunItem,
    RNPVRunListResponse,
)
from app.service import ServiceContainer

router = APIRouter(prefix="/api", tags=["pipeline", "rnpv"])


def _raise_service_error(result, *, validation_status: int = 400) -> None:
    if result.success:
        return
    status_code = validation_status if result.error_code == "VALIDATION_ERROR" else 500
    raise HTTPException(status_code=status_code, detail=result.message)


@router.get("/pipeline/drugs", response_model=PipelineDrugListResponse)
def list_pipeline_drugs(
    stock_code: str = Query(..., description="stock code"),
    container: ServiceContainer = Depends(get_container),
):
    result = container.pipeline.list_drugs(stock_code, include_terminal=True)
    _raise_service_error(result)
    items = [PipelineDrugItem(**item) for item in (result.data or [])]
    return PipelineDrugListResponse(
        stock_code=stock_code,
        total=len(items),
        items=items,
    )


@router.post("/pipeline/upsert-drugs", response_model=PipelineDrugUpsertResponse)
def upsert_pipeline_drugs(
    payload: PipelineDrugUpsertRequest,
    container: ServiceContainer = Depends(get_container),
):
    result = container.pipeline.upsert_drugs(
        [item.model_dump(exclude_none=True) for item in payload.items]
    )
    _raise_service_error(result)
    return PipelineDrugUpsertResponse(**(result.data or {}))


@router.post("/pipeline/rebuild-embeddings")
def rebuild_pipeline_embeddings(
    stock_code: str | None = Query(None, description="optional stock code"),
    container: ServiceContainer = Depends(get_container),
):
    result = container.pipeline.rebuild_embeddings(stock_code=stock_code)
    _raise_service_error(result)
    return result.data or {"synced_chunks": 0}


@router.get("/rnpv/runs", response_model=RNPVRunListResponse)
def list_rnpv_runs(
    stock_code: str = Query(..., description="stock code"),
    limit: int = Query(10, ge=1, le=100),
    container: ServiceContainer = Depends(get_container),
):
    result = container.pipeline.list_runs(stock_code, limit=limit)
    _raise_service_error(result)
    items = [RNPVRunItem(**item) for item in (result.data or [])]
    return RNPVRunListResponse(
        stock_code=stock_code,
        total=len(items),
        items=items,
    )


@router.post("/rnpv/runs", response_model=RNPVRunItem)
def create_rnpv_run(
    payload: RNPVRunCreate,
    container: ServiceContainer = Depends(get_container),
):
    result = container.pipeline.upsert_run(
        run_uid=payload.run_uid,
        stock_code=payload.stock_code,
        input_params=payload.input_params,
        scenario_results=payload.scenario_results,
        pipeline_drug_id=payload.pipeline_drug_id,
        evidence_refs=payload.evidence_refs,
        warnings=payload.warnings,
        created_by=payload.created_by,
    )
    _raise_service_error(result, validation_status=422)
    return RNPVRunItem(**(result.data or {}))
