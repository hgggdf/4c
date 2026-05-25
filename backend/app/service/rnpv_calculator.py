"""
rNPV 计算核心。
输入结构化参数字典，输出悲观/基准/乐观三情景结果。
不依赖数据库，纯数学计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.service.rnpv_params import (
    DEFAULT_WACC,
    PHASE_ORDER,
    SCENARIO_MULTIPLIERS,
    STAGE_ANNUAL_COST_CNY_WAN,
    YEARS_TO_APPROVAL,
    get_penetration_curve,
    get_pos_matrix,
    normalize_phase,
)


@dataclass
class RnpvInput:
    """用户提供（或 Agent 追问收集）的参数，缺失字段用 None 表示，计算时走 fallback。"""
    stock_code: str
    stock_name: str
    drug_name: str
    indication: str | None = None
    trial_phase: str | None = None          # 标准化枚举
    route_of_administration: str | None = None
    target_patients_wan: float | None = None  # 目标患者数（万人）
    price_per_year_wan: float | None = None   # 年治疗费用（万元/人）
    peak_market_share: float | None = None    # 峰值市场份额（0-1）
    net_margin: float = 0.25                  # 净利润率，默认25%
    wacc: float = DEFAULT_WACC
    expected_approval_year: int | None = None
    rd_expense_total_wan: float | None = None # 公司整体 R&D 费用（万元），用于成本代理


@dataclass
class ScenarioResult:
    label: str
    rnpv_wan: float          # 万元人民币
    pos_cumulative: float
    peak_revenue_wan: float
    total_cost_wan: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RnpvResult:
    drug_name: str
    stock_name: str
    trial_phase: str
    indication: str
    bear: ScenarioResult
    base: ScenarioResult
    bull: ScenarioResult
    assumptions: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _cumulative_pos(phase: str, pos_matrix: dict[str, float], multiplier: float = 1.0) -> float:
    """从当前阶段累积计算到上市的 PoS，multiplier 用于情景调整。"""
    idx = PHASE_ORDER.index(phase)
    remaining = PHASE_ORDER[idx:-1]  # 不含 approved
    cum = 1.0
    for p in remaining:
        raw = pos_matrix.get(p, 0.5)
        cum *= min(raw * multiplier, 1.0)
    return cum


def _calc_revenue_npv(
    patients_wan: float,
    price_wan: float,
    peak_share: float,
    net_margin: float,
    penetration_curve: list[float],
    approval_year_offset: float,
    wacc: float,
) -> float:
    """计算上市后收入端 NPV（万元），从当前时间点折现。
    patients_wan: 万人；price_wan: 万元/人/年
    年峰值销售额 = patients_wan × 10000 × price_wan（万元）× peak_share × penetration
    """
    npv = 0.0
    for i, pen in enumerate(penetration_curve):
        year = approval_year_offset + i + 1
        # patients_wan 单位是万人，price_wan 单位是万元/人，相乘再乘 10000 得万元
        annual_revenue = patients_wan * 10000 * price_wan * peak_share * pen * net_margin
        npv += annual_revenue / (1 + wacc) ** year
    return npv


def _calc_cost_npv(
    phase: str,
    rd_total_wan: float | None,
    wacc: float,
) -> float:
    """计算研发成本端 NPV（万元）。"""
    idx = PHASE_ORDER.index(phase)
    remaining_phases = PHASE_ORDER[idx:-1]
    cost_npv = 0.0
    offset = 0.0
    for p in remaining_phases:
        annual = STAGE_ANNUAL_COST_CNY_WAN.get(p, 5_000)
        # 若有公司真实 R&D 数据，用分摊系数覆盖内置值
        if rd_total_wan:
            from app.service.rnpv_params import PIPELINE_COST_ALLOCATION_RATIO
            annual = rd_total_wan * PIPELINE_COST_ALLOCATION_RATIO / max(len(remaining_phases), 1)
        duration = 1.5  # 每阶段平均 1.5 年
        mid_year = offset + duration / 2
        cost_npv += annual * duration / (1 + wacc) ** mid_year
        offset += duration
    return cost_npv


def _calc_scenario(
    inp: RnpvInput,
    scenario: str,
    phase: str,
    pos_matrix: dict[str, float],
    penetration_curve: list[float],
) -> ScenarioResult:
    mult = SCENARIO_MULTIPLIERS[scenario]

    pos = _cumulative_pos(phase, pos_matrix, multiplier=mult["pos"])
    approval_offset = YEARS_TO_APPROVAL.get(phase, 3.0)

    patients = inp.target_patients_wan or 50.0      # fallback: 50万患者
    price = inp.price_per_year_wan or 5.0           # fallback: 5万/年
    peak_share = (inp.peak_market_share or 0.15) * mult["peak_share"]
    price_adj = price * mult["price"]

    peak_revenue = patients * 10000 * price_adj * min(peak_share, 1.0)

    rev_npv = _calc_revenue_npv(
        patients, price_adj, min(peak_share, 1.0),
        inp.net_margin, penetration_curve,
        approval_offset, inp.wacc,
    )
    cost_npv = _calc_cost_npv(phase, inp.rd_expense_total_wan, inp.wacc)

    rnpv = pos * rev_npv - cost_npv

    return ScenarioResult(
        label={"bear": "悲观", "base": "基准", "bull": "乐观"}[scenario],
        rnpv_wan=round(rnpv, 1),
        pos_cumulative=round(pos, 4),
        peak_revenue_wan=round(peak_revenue, 1),
        total_cost_wan=round(cost_npv, 1),
        details={
            "patients_wan": patients,
            "price_wan": price_adj,
            "peak_share_pct": round(min(peak_share, 1.0) * 100, 1),
            "approval_offset_years": approval_offset,
        },
    )


def calculate_rnpv(inp: RnpvInput) -> RnpvResult:
    """主入口：接受 RnpvInput，返回三情景 RnpvResult。"""
    warnings: list[str] = []

    # 标准化 trial_phase
    phase = inp.trial_phase
    if phase and phase not in PHASE_ORDER:
        phase = normalize_phase(phase)
    if not phase or phase not in PHASE_ORDER[:-1]:
        phase = "phase2"
        warnings.append("临床阶段未提供或无法识别，已按 Phase II 估算。")

    if phase == "approved":
        warnings.append("该药品已上市，rNPV 模型不适用，建议直接使用收入预测模型。")
        phase = "nda"

    pos_matrix = get_pos_matrix(inp.indication)
    penetration_curve = get_penetration_curve(inp.route_of_administration)

    if inp.target_patients_wan is None:
        warnings.append("目标患者数未提供，已按行业基准（50万人）估算。")
    if inp.price_per_year_wan is None:
        warnings.append("年治疗费用未提供，已按基准（5万元/人/年）估算。")
    if inp.peak_market_share is None:
        warnings.append("峰值市场份额未提供，已按基准（15%）估算。")

    bear = _calc_scenario(inp, "bear", phase, pos_matrix, penetration_curve)
    base = _calc_scenario(inp, "base", phase, pos_matrix, penetration_curve)
    bull = _calc_scenario(inp, "bull", phase, pos_matrix, penetration_curve)

    assumptions = {
        "trial_phase": phase,
        "wacc_pct": inp.wacc * 100,
        "net_margin_pct": inp.net_margin * 100,
        "pos_matrix_domain": "oncology" if pos_matrix != get_pos_matrix(None) else "default",
        "penetration_type": "injectable" if penetration_curve[0] == 0.05 else "oral",
        "data_source": "行业基准（BIO 2011-2020） + 用户输入",
    }

    return RnpvResult(
        drug_name=inp.drug_name,
        stock_name=inp.stock_name,
        trial_phase=phase,
        indication=inp.indication or "未知",
        bear=bear,
        base=base,
        bull=bull,
        assumptions=assumptions,
        warnings=warnings,
    )


def format_rnpv_result(result: RnpvResult) -> dict[str, Any]:
    """将 RnpvResult 序列化为前端可直接消费的字典。"""
    def fmt_scenario(s: ScenarioResult) -> dict:
        return {
            "label": s.label,
            "rnpv_wan": s.rnpv_wan,
            "rnpv_yi": round(s.rnpv_wan / 10_000, 2),  # 亿元
            "pos_pct": round(s.pos_cumulative * 100, 1),
            "peak_revenue_wan": s.peak_revenue_wan,
            "total_cost_wan": s.total_cost_wan,
            "details": s.details,
        }

    return {
        "type": "rnpv_result",
        "drug_name": result.drug_name,
        "stock_name": result.stock_name,
        "trial_phase": result.trial_phase,
        "indication": result.indication,
        "scenarios": {
            "bear": fmt_scenario(result.bear),
            "base": fmt_scenario(result.base),
            "bull": fmt_scenario(result.bull),
        },
        "assumptions": result.assumptions,
        "warnings": result.warnings,
    }
