"""宏观指标名称归一化映射（统一维护，多处引用）。"""

from __future__ import annotations

from typing import Any


MACRO_DISPLAY_NAMES: dict[str, str] = {
    "GDP": "GDP增速",
    "CPI": "CPI同比",
    "PPI": "PPI同比",
    "PMI": "PMI",
    "社融": "社融存量同比",
    "医药研发投入": "医药研发投入增速",
}

MACRO_DESCRIPTIONS: dict[str, str] = {
    "GDP": "国内生产总值(GDP)同比增速，反映宏观经济总量变化",
    "CPI": "居民消费价格指数(CPI)同比变化，反映通货膨胀水平",
    "PPI": "工业生产者出厂价格指数(PPI)同比变化，反映工业品价格走势",
    "PMI": "制造业采购经理指数，50以上为扩张区间",
    "社融": "社会融资规模存量同比增速，衡量宏观流动性",
    "医药研发投入": "医药行业研发投入同比增速",
}


def normalize_macro_record(rec: dict[str, Any]) -> dict[str, Any]:
    rec = dict(rec)
    raw_name = rec.get("indicator_name", "")
    display_name = MACRO_DISPLAY_NAMES.get(raw_name, raw_name)
    rec["indicator_name"] = display_name
    period = rec.get("period", "")
    value = rec.get("value")
    unit = rec.get("unit", "")
    desc = MACRO_DESCRIPTIONS.get(raw_name, "")
    val_str = f"{value}{unit}" if value is not None else "--"
    rec["summary_text"] = f"{period} {display_name}为{val_str}。{desc}" if desc else f"{period} {display_name}: {val_str}"
    return rec
