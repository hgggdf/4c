from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from app.service.analysis_service import AnalysisService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
analysis_service = AnalysisService()


class DimensionOut(BaseModel):
    name: str
    score: float
    comment: str
    metrics: dict


class DiagnoseOut(BaseModel):
    stock_code: str
    stock_name: str
    year: int
    total_score: float
    level: str
    dimensions: list[DimensionOut]
    strengths: list[str]
    weaknesses: list[str]
    suggestion: str


@router.get("/diagnose", response_model=DiagnoseOut)
def diagnose_company(
    symbol: str = Query(..., description="股票代码，如 600276"),
    year: int = Query(2024, description="年份"),
    db: Session = Depends(get_db),
):
    result = analysis_service.diagnose(db, symbol, year)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的财务数据")

    return DiagnoseOut(
        stock_code=result.stock_code,
        stock_name=result.stock_name,
        year=result.year,
        total_score=result.total_score,
        level=result.level,
        dimensions=[
            DimensionOut(
                name=d.name,
                score=d.score,
                comment=d.comment,
                metrics={k: {"value": v[0], "unit": v[1], "score": v[2]}
                         for k, v in d.metrics.items()},
            )
            for d in result.dimensions
        ],
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        suggestion=result.suggestion,
    )


@router.get("/risks")
def get_risks(
    symbols: str = Query(
        "600276,603259,300015",
        description="逗号分隔的股票代码列表",
    ),
    db: Session = Depends(get_db),
):
    codes = [s.strip() for s in symbols.split(",") if s.strip()]
    results = analysis_service.scan_risks(db, codes)
    return {"total": len(results), "data": results}


@router.get("/compare")
def compare_companies(
    metric: str = Query(..., description="指标名，如 毛利率"),
    year: int = Query(2024),
    symbols: str = Query("600276,603259,300015"),
    db: Session = Depends(get_db),
):
    codes = [s.strip() for s in symbols.split(",") if s.strip()]
    return analysis_service.compare_metric(db, metric, year, codes)


@router.get("/trend")
def get_metric_trend(
    symbol: str = Query(..., description="股票代码"),
    metric: str = Query(..., description="指标名"),
    db: Session = Depends(get_db),
):
    return analysis_service.get_metric_trend(db, symbol, metric)
