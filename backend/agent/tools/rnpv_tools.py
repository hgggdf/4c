"""rNPV 管线估值工具函数"""

from __future__ import annotations

import uuid
from typing import Any

from app.service.container import ServiceContainer
from app.service.rnpv_calculator import RnpvInput, calculate_rnpv, format_rnpv_result


def get_pipeline_drugs(stock_code: str) -> list[dict]:
    """通过 PipelineService 获取适合 rNPV 自动选择的管线候选。"""
    container = ServiceContainer.build_default()
    result = container.pipeline.list_rnpv_candidates(stock_code)
    if not result.success:
        raise ValueError(f"获取管线品种失败: {result.message}")
    return result.data or []


def _resolve_drug_params(
    stock_code: str,
    drug_name: str | None,
    indication: str | None,
    trial_phase: str | None,
    route_of_administration: str | None,
) -> tuple[str, str | None, str | None, str | None, int | None]:
    """从管线库补全缺失字段，返回 (drug_name, indication, trial_phase, route, pipeline_drug_id)。"""
    pipeline_drug_id: int | None = None
    if drug_name is None or trial_phase is None:
        drugs = get_pipeline_drugs(stock_code)
        if drugs:
            first = drugs[0]
            drug_name = drug_name or first.get("drug_name", "在研品种")
            indication = indication or first.get("indication")
            trial_phase = trial_phase or first.get("trial_phase")
            route_of_administration = route_of_administration or first.get("route_of_administration")
            pipeline_drug_id = first.get("id")
        else:
            drug_name = drug_name or "在研品种"
    return drug_name, indication, trial_phase, route_of_administration, pipeline_drug_id


def calculate_pipeline_rnpv(
    stock_code: str,
    stock_name: str,
    drug_name: str | None = None,
    indication: str | None = None,
    trial_phase: str | None = None,
    route_of_administration: str | None = None,
    target_patients_wan: float | None = None,
    price_per_year_wan: float | None = None,
    peak_market_share: float | None = None,
    net_margin: float = 0.25,
    wacc: float = 0.10,
    rd_expense_total_wan: float | None = None,
) -> dict[str, Any]:
    """
    计算单个管线品种的 rNPV 三情景估值。

    若 drug_name 未指定，自动取该公司管线列表中的第一个品种。
    参数缺失时均有行业基准 fallback，不会报错。
    """
    drug_name, indication, trial_phase, route_of_administration, _ = _resolve_drug_params(
        stock_code, drug_name, indication, trial_phase, route_of_administration
    )

    inp = RnpvInput(
        stock_code=stock_code,
        stock_name=stock_name,
        drug_name=drug_name,
        indication=indication,
        trial_phase=trial_phase,
        route_of_administration=route_of_administration,
        target_patients_wan=target_patients_wan,
        price_per_year_wan=price_per_year_wan,
        peak_market_share=peak_market_share,
        net_margin=net_margin,
        wacc=wacc,
        rd_expense_total_wan=rd_expense_total_wan,
    )

    result = calculate_rnpv(inp)
    return format_rnpv_result(result)


def calculate_and_save_pipeline_rnpv(
    stock_code: str,
    stock_name: str,
    drug_name: str | None = None,
    indication: str | None = None,
    trial_phase: str | None = None,
    route_of_administration: str | None = None,
    target_patients_wan: float | None = None,
    price_per_year_wan: float | None = None,
    peak_market_share: float | None = None,
    net_margin: float = 0.25,
    wacc: float = 0.10,
    rd_expense_total_wan: float | None = None,
) -> dict[str, Any]:
    """
    计算 rNPV 三情景估值并写入 rnpv_valuation_runs 表。

    返回值在 format_rnpv_result 基础上追加 run_id 和 run_uid，
    前端可用 run_uid 通过 /api/rnpv/runs?stock_code=... 查询历史。
    """
    drug_name, indication, trial_phase, route_of_administration, pipeline_drug_id = (
        _resolve_drug_params(stock_code, drug_name, indication, trial_phase, route_of_administration)
    )

    inp = RnpvInput(
        stock_code=stock_code,
        stock_name=stock_name,
        drug_name=drug_name,
        indication=indication,
        trial_phase=trial_phase,
        route_of_administration=route_of_administration,
        target_patients_wan=target_patients_wan,
        price_per_year_wan=price_per_year_wan,
        peak_market_share=peak_market_share,
        net_margin=net_margin,
        wacc=wacc,
        rd_expense_total_wan=rd_expense_total_wan,
    )

    rnpv_result = calculate_rnpv(inp)
    formatted = format_rnpv_result(rnpv_result)

    input_params = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "drug_name": drug_name,
        "indication": indication,
        "trial_phase": trial_phase,
        "route_of_administration": route_of_administration,
        "target_patients_wan": target_patients_wan,
        "price_per_year_wan": price_per_year_wan,
        "peak_market_share": peak_market_share,
        "net_margin": net_margin,
        "wacc": wacc,
        "rd_expense_total_wan": rd_expense_total_wan,
    }

    run_uid = str(uuid.uuid4())
    container = ServiceContainer.build_default()
    save_result = container.pipeline.upsert_run(
        run_uid=run_uid,
        stock_code=stock_code,
        input_params=input_params,
        scenario_results=formatted["scenarios"],
        pipeline_drug_id=pipeline_drug_id,
        evidence_refs=None,
        warnings=formatted.get("warnings"),
        created_by="aiagent",
    )

    formatted["run_uid"] = run_uid
    formatted["run_id"] = save_result.data.get("id") if save_result.success and save_result.data else None

    return formatted


def list_pipeline_drugs(stock_code: str) -> list[dict[str, Any]]:
    """列出公司管线品种，供用户选择要估值的品种。"""
    drugs = get_pipeline_drugs(stock_code)
    return [
        {
            "drug_name": d.get("drug_name"),
            "indication": d.get("indication"),
            "trial_phase": d.get("trial_phase"),
            "route_of_administration": d.get("route_of_administration"),
            "expected_approval_year": d.get("expected_approval_year"),
        }
        for d in drugs
    ]
