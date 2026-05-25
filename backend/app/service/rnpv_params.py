"""
rNPV 内置行业基准参数表。
所有数值来源于 BIO 2011-2020 行业报告，不依赖外部 API 或数据库。
"""

from __future__ import annotations

# ── 临床阶段枚举 ──────────────────────────────────────────────
PHASE_ORDER = ["phase1", "phase2", "phase3", "nda", "approved"]

# trial_phase 原始文本 → 标准枚举（入库侧未清洗时的兜底映射）
PHASE_NORMALIZE: dict[str, str] = {
    "i期": "phase1", "phase i": "phase1", "phase1": "phase1", "一期": "phase1",
    "ii期": "phase2", "phase ii": "phase2", "phase2": "phase2", "二期": "phase2",
    "iii期": "phase3", "phase iii": "phase3", "phase3": "phase3", "三期": "phase3",
    "nda": "nda", "申报": "nda", "上市申请": "nda", "bla": "nda",
    "approved": "approved", "上市": "approved", "已上市": "approved",
}

# ── PoS 基准矩阵（阶段间转化成功率）─────────────────────────
# 结构：{治疗领域: {当前阶段: 到下一阶段的成功率}}
POS_MATRIX: dict[str, dict[str, float]] = {
    "oncology": {
        "phase1": 0.45,
        "phase2": 0.27,
        "phase3": 0.50,
        "nda":    0.93,
    },
    "default": {
        "phase1": 0.56,
        "phase2": 0.31,
        "phase3": 0.62,
        "nda":    0.88,
    },
}

# 适应症关键词 → 治疗领域
INDICATION_TO_DOMAIN: dict[str, str] = {
    "肿瘤": "oncology", "癌": "oncology", "白血病": "oncology",
    "淋巴瘤": "oncology", "骨髓瘤": "oncology",
}

# ── 渗透率曲线（上市后第 1-10 年）────────────────────────────
# 结构：{给药方式类型: [year1, year2, ..., year10]}
PENETRATION_CURVES: dict[str, list[float]] = {
    "oral":       [0.15, 0.35, 0.55, 0.65, 0.70, 0.72, 0.72, 0.70, 0.65, 0.55],
    "injectable": [0.05, 0.15, 0.30, 0.45, 0.50, 0.52, 0.52, 0.50, 0.45, 0.38],
}

ROUTE_TO_CURVE: dict[str, str] = {
    "口服": "oral", "片剂": "oral", "胶囊": "oral",
    "注射": "injectable", "静脉": "injectable", "皮下": "injectable", "生物制剂": "injectable",
}

# ── 折现率 ────────────────────────────────────────────────────
DEFAULT_WACC = 0.10

# ── 阶段到上市预计剩余年数（行业均值）────────────────────────
YEARS_TO_APPROVAL: dict[str, float] = {
    "phase1": 8.0,
    "phase2": 5.5,
    "phase3": 3.0,
    "nda":    1.0,
    "approved": 0.0,
}

# ── 情景偏移系数 ──────────────────────────────────────────────
SCENARIO_MULTIPLIERS: dict[str, dict[str, float]] = {
    "bear": {"pos": 0.70, "peak_share": 0.70, "price": 0.85},
    "base": {"pos": 1.00, "peak_share": 1.00, "price": 1.00},
    "bull": {"pos": 1.20, "peak_share": 1.30, "price": 1.15},
}

# ── 成本代理参数 ──────────────────────────────────────────────
# 单品种 R&D 费用 ≈ 公司总 R&D × 分摊系数
PIPELINE_COST_ALLOCATION_RATIO = 0.30

# 各阶段行业平均年研发费用（万元人民币，粗略基准）
STAGE_ANNUAL_COST_CNY_WAN: dict[str, float] = {
    "phase1": 2_000,
    "phase2": 8_000,
    "phase3": 30_000,
    "nda":    5_000,
}


def normalize_phase(raw: str) -> str | None:
    """将原始 trial_phase 文本标准化为枚举值，无法识别返回 None。"""
    return PHASE_NORMALIZE.get(raw.strip().lower())


def get_pos_matrix(indication: str | None) -> dict[str, float]:
    """根据适应症文本返回对应的 PoS 矩阵。"""
    if indication:
        for kw, domain in INDICATION_TO_DOMAIN.items():
            if kw in indication:
                return POS_MATRIX[domain]
    return POS_MATRIX["default"]


def get_penetration_curve(route: str | None) -> list[float]:
    """根据给药方式返回渗透率曲线，缺失时返回口服曲线。"""
    if route:
        for kw, curve_key in ROUTE_TO_CURVE.items():
            if kw in route:
                return PENETRATION_CURVES[curve_key]
    return PENETRATION_CURVES["oral"]
