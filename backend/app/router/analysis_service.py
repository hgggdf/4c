"""Backward-compatible entrypoint for the analysis service."""

from app.service.analysis_service import AnalysisService, DiagnoseResult, DimensionScore

__all__ = ["AnalysisService", "DiagnoseResult", "DimensionScore"]
