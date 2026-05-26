"""rNPV run payload 软契约校验。

数据库里两个 JSON 列没有 schema，所以这里给出最小字段集和值域检查，
在写入 rnpv_valuation_runs 之前 fail-fast，避免 prompt/agent 漂移后历史数据无法横向对比。
"""

from __future__ import annotations

from typing import Any


REQUIRED_SCENARIOS = ("base", "bear", "bull")
REQUIRED_INPUT_FIELDS = ("discount_rate", "horizon_years", "scenarios")
REQUIRED_SCENARIO_INPUT_FIELDS = ("pos", "peak_share", "price", "patient_count")
REQUIRED_RESULT_FIELDS = ("rnpv_total",)


class RNPVValidationError(ValueError):
    """rNPV 输入/结果不符合最小契约。"""


def _ensure_dict(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RNPVValidationError(f"{where} 必须是对象，实际为 {type(value).__name__}")
    return value


def _ensure_finite_number(value: Any, where: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RNPVValidationError(f"{where} 必须是数字")
    fval = float(value)
    if fval != fval or fval in (float("inf"), float("-inf")):
        raise RNPVValidationError(f"{where} 必须是有限数")
    if not allow_zero and fval == 0:
        raise RNPVValidationError(f"{where} 不能为 0")
    return fval


def validate_input_params(payload: Any) -> dict[str, Any]:
    data = _ensure_dict(payload, "input_params_json")

    for field in REQUIRED_INPUT_FIELDS:
        if field not in data:
            raise RNPVValidationError(f"input_params_json 缺少字段 {field}")

    discount_rate = _ensure_finite_number(data["discount_rate"], "discount_rate")
    if not 0 < discount_rate < 1:
        raise RNPVValidationError("discount_rate 必须在 (0, 1) 之间")

    horizon_years = data["horizon_years"]
    if not isinstance(horizon_years, int) or isinstance(horizon_years, bool):
        raise RNPVValidationError("horizon_years 必须是整数")
    if not 1 <= horizon_years <= 50:
        raise RNPVValidationError("horizon_years 必须在 [1, 50] 之间")

    scenarios = _ensure_dict(data["scenarios"], "input_params_json.scenarios")
    for name in REQUIRED_SCENARIOS:
        if name not in scenarios:
            raise RNPVValidationError(f"input_params_json.scenarios 缺少 {name}")
        scenario = _ensure_dict(scenarios[name], f"scenarios.{name}")
        for field in REQUIRED_SCENARIO_INPUT_FIELDS:
            if field not in scenario:
                raise RNPVValidationError(f"scenarios.{name} 缺少 {field}")
        pos = _ensure_finite_number(scenario["pos"], f"scenarios.{name}.pos")
        if not 0 <= pos <= 1:
            raise RNPVValidationError(f"scenarios.{name}.pos 必须在 [0, 1] 之间")
        peak_share = _ensure_finite_number(scenario["peak_share"], f"scenarios.{name}.peak_share")
        if not 0 <= peak_share <= 1:
            raise RNPVValidationError(f"scenarios.{name}.peak_share 必须在 [0, 1] 之间")
        _ensure_finite_number(scenario["price"], f"scenarios.{name}.price")
        patient_count = _ensure_finite_number(
            scenario["patient_count"], f"scenarios.{name}.patient_count"
        )
        if patient_count < 0:
            raise RNPVValidationError(f"scenarios.{name}.patient_count 不能为负")

    return data


def validate_scenario_results(payload: Any) -> dict[str, Any]:
    data = _ensure_dict(payload, "scenario_results_json")
    for name in REQUIRED_SCENARIOS:
        if name not in data:
            raise RNPVValidationError(f"scenario_results_json 缺少 {name}")
        result = _ensure_dict(data[name], f"scenario_results_json.{name}")
        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                raise RNPVValidationError(f"scenario_results_json.{name} 缺少 {field}")
        _ensure_finite_number(result["rnpv_total"], f"scenario_results_json.{name}.rnpv_total")
    return data


def validate_run_payload(
    *,
    input_params: Any,
    scenario_results: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """同时校验输入与结果。返回原样 payload，便于写库。"""
    return validate_input_params(input_params), validate_scenario_results(scenario_results)
