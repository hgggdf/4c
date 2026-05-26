"""管线字段标准化与升级守卫。

trial_phase / therapeutic_area 的合法取值都集中在这里；
import 链路在写库前调用 normalize_*；
write_repository 在 upsert 时调用 phase_progresses 守住降级。
"""

from __future__ import annotations

from typing import Iterable

# trial_phase: 单值的合法集合 + 比较序
PHASE_ORDER: dict[str, int] = {
    "preclinical": 0,
    "phase1": 1,
    "phase1_2": 2,
    "phase2": 3,
    "phase2_3": 4,
    "phase3": 5,
    "nda": 6,
    "nda_rejected": 6,  # 与 NDA 同序：被拒后回到提交点
    "approved": 7,
    "terminated": -1,   # 终止/撤回是合法的"回退"，与升级序无关
    "withdrawn": -1,
    "unknown": -2,
}

VALID_PHASES = frozenset(PHASE_ORDER.keys())

# 原始表述 → 标准枚举
_PHASE_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("已上市", "已获批", "获批上市", "批准上市", "approved"), "approved"),
    (("nda被拒", "上市申请被拒", "nda_rejected"), "nda_rejected"),
    (("nda", "申报上市", "上市申请", "已申报"), "nda"),
    (("ii/iii期", "2/3期", "二三期", "phase2_3", "phase 2/3"), "phase2_3"),
    (("i/ii期", "1/2期", "一二期", "phase1_2", "phase 1/2"), "phase1_2"),
    (("iii期", "3期", "三期", "phase iii", "phase3", "phase 3"), "phase3"),
    (("ii期", "2期", "二期", "phase ii", "phase2", "phase 2"), "phase2"),
    (("i期", "1期", "一期", "phase i", "phase1", "phase 1"), "phase1"),
    (("临床前", "preclinical", "ind"), "preclinical"),
    (("终止", "已终止", "terminated"), "terminated"),
    (("撤回", "已撤回", "暂停", "suspended", "withdrawn"), "withdrawn"),
]


def normalize_trial_phase(raw: str | None) -> str:
    """把任意原始表述映射到标准枚举；映射不到返回 unknown。"""
    if not raw:
        return "unknown"
    text = str(raw).strip().lower()
    if not text:
        return "unknown"
    if text in VALID_PHASES:
        return text
    for keywords, target in _PHASE_PATTERNS:
        for kw in keywords:
            if kw.lower() in text:
                return target
    return "unknown"


_AREA_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("肿瘤", "癌", "oncology", "cancer"), "oncology"),
    (("心血管", "心脏", "cardio"), "cardiovascular"),
    (("代谢", "糖尿", "metabolic"), "metabolic"),
    (("免疫", "自免", "immunology", "immune"), "immunology"),
    (("感染", "病毒", "infection", "antiviral"), "infection"),
    (("神经", "中枢", "cns", "neuro"), "cns"),
    (("罕见病", "孤儿药", "rare"), "rare_disease"),
    (("疫苗", "vaccine"), "vaccine"),
    (("眼科", "ophthalmology", "ophthalmic"), "ophthalmology"),
]

VALID_AREAS = frozenset(
    {target for _, target in _AREA_PATTERNS} | {"other"}
)


def normalize_therapeutic_area(raw: str | None) -> str:
    if not raw:
        return "other"
    text = str(raw).strip().lower()
    if not text:
        return "other"
    if text in VALID_AREAS:
        return text
    for keywords, target in _AREA_PATTERNS:
        for kw in keywords:
            if kw.lower() in text:
                return target
    return "other"


def phase_progresses(old_phase: str | None, new_phase: str | None) -> bool:
    """新阶段是否允许覆盖旧阶段。

    规则：
    - 旧值为空 → 直接允许。
    - 新值是 terminated/withdrawn → 允许（合法回退）。
    - 旧值已是 terminated/withdrawn → 也允许覆盖回 active 阶段（人工纠错）。
    - 否则要求 PHASE_ORDER[new] >= PHASE_ORDER[old]。
    """
    if not old_phase:
        return True
    new_phase = new_phase or "unknown"
    if new_phase in {"terminated", "withdrawn"}:
        return True
    if old_phase in {"terminated", "withdrawn"}:
        return True
    return PHASE_ORDER.get(new_phase, -2) >= PHASE_ORDER.get(old_phase, -2)


def merge_aliases(existing: Iterable[str] | None, *new_values: str | None) -> list[str]:
    """合并别名列表：保留顺序、去重、忽略空值。"""
    seen: dict[str, None] = {}
    for source in (existing or []):
        if source:
            seen.setdefault(str(source).strip(), None)
    for value in new_values:
        if value:
            seen.setdefault(str(value).strip(), None)
    return [k for k in seen.keys() if k]
