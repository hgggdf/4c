"""Pipeline / rNPV 路由 schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PipelineDrugItem(BaseModel):
    id: int
    stock_code: str
    drug_name: str
    canonical_drug_name: str | None = None
    indication: str | None = None
    indication_norm: str | None = None
    therapeutic_area: str | None = None
    trial_phase: str
    trial_phase_raw: str | None = None
    route_of_administration: str | None = None
    confidence_score: float | None = None
    source_type: str | None = None
    source_url: str | None = None
    evidence_text: str | None = None
    aliases: list[str] = Field(default_factory=list)


class PipelineDrugListResponse(BaseModel):
    stock_code: str
    total: int
    items: list[PipelineDrugItem]


class PipelineDrugUpsert(BaseModel):
    stock_code: str
    drug_name: str
    canonical_drug_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    indication: str | None = None
    indication_norm: str | None = None
    therapeutic_area: str | None = None
    trial_phase: str
    trial_phase_raw: str | None = None
    route_of_administration: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_table: str | None = None
    source_id: int | None = None
    source_uid: str | None = None
    evidence_text: str = ""
    confidence_score: float | None = None


class PipelineDrugUpsertRequest(BaseModel):
    items: list[PipelineDrugUpsert]


class PipelineDrugUpsertResponse(BaseModel):
    created: int
    updated: int
    warnings: list[str] = Field(default_factory=list)


class RNPVScenarioInput(BaseModel):
    pos: float
    peak_share: float
    price: float
    patient_count: float


class RNPVInputParams(BaseModel):
    discount_rate: float
    horizon_years: int
    scenarios: dict[str, RNPVScenarioInput]


class RNPVRunCreate(BaseModel):
    run_uid: str
    stock_code: str
    pipeline_drug_id: int | None = None
    input_params: dict[str, Any]
    scenario_results: dict[str, Any]
    evidence_refs: list[dict[str, Any]] | None = None
    warnings: list[str] | None = None
    created_by: str = "aiagent"


class RNPVRunItem(BaseModel):
    id: int
    run_uid: str
    stock_code: str
    pipeline_drug_id: int | None
    input_params: dict[str, Any]
    scenario_results: dict[str, Any]
    evidence_refs: list[dict[str, Any]] | None = None
    warnings: list[str] | None = None
    created_by: str
    created_at: str


class RNPVRunListResponse(BaseModel):
    stock_code: str
    total: int
    items: list[RNPVRunItem]
