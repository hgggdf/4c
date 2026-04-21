"""已废弃的旧脚本。

该脚本依赖旧的 financial_data 表及对应仓储命名，
不再兼容当前 MySQL-only 结构化模型主链，保留仅用于历史参考。
"""
from __future__ import annotations

LEGACY_SCRIPT_MESSAGE = (
    "Deprecated legacy script: scripts/import_financial_data.py 依赖旧 financial_data 链路，"
    "当前主链已切换到结构化热表/归档表模型。该脚本仅保留作历史参考。"
)

if __name__ == "__main__":
    raise SystemExit(LEGACY_SCRIPT_MESSAGE)

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import akshare as ak
from sqlalchemy.orm import Session
from core.database.session import engine
from core.repositories.financial_repo import FinancialDataRepository

COMPANIES = [
    ("600276", "恒瑞医药"),
    ("603259", "药明康德"),
    ("300015", "爱尔眼科"),
]

YEARS = ["2022", "2023", "2024"]

# akshare列名 -> 标准指标名, 单位
METRIC_MAP = {
    "营业总收入":     ("营业总收入", "亿元"),
    "净利润":         ("净利润", "亿元"),
    "扣非净利润":     ("扣非净利润", "亿元"),
    "销售毛利率":     ("毛利率", "%"),
    "销售净利率":     ("净利率", "%"),
    "净资产收益率":   ("ROE", "%"),
    "资产负债率":     ("资产负债率", "%"),
    "基本每股收益":   ("每股收益", "元"),
    "每股净资产":     ("每股净资产", "元"),
    "流动比率":       ("流动比率", ""),
    "速动比率":       ("速动比率", ""),
    "存货周转率":     ("存货周转率", "次"),
    "应收账款周转天数": ("应收账款周转天数", "天"),
}


def _parse_value(raw) -> float | None:
    """把 '39.06亿' / '17.93%' / '0.61' 统一转成 float"""
    if raw is None or raw is False or str(raw).strip() in ("False", "—", "-", ""):
        return None
    s = str(raw).strip()
    s = s.replace(",", "").replace("，", "")
    # 去掉单位
    s = re.sub(r"[亿万元%次天]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def import_financial_data() -> None:
    """抓取目标公司的年度财务摘要并写入 financial_data 表。"""
    repo = FinancialDataRepository()

    for code, name in COMPANIES:
        print(f"\n正在采集 {name}({code}) 财务数据...")
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
        except Exception as e:
            print(f"  [FAIL] 获取数据失败: {e}")
            continue

        # 只取目标年份
        df["_year"] = df["报告期"].astype(str).str[:4]
        df_target = df[df["_year"].isin(YEARS)]

        if df_target.empty:
            print(f"  [WARN] 无近3年数据")
            continue

        records = []
        for _, row in df_target.iterrows():
            year = int(row["_year"])
            for col, (metric_name, unit) in METRIC_MAP.items():
                if col not in row:
                    continue
                val = _parse_value(row[col])
                records.append({
                    "stock_code": code,
                    "stock_name": name,
                    "year": year,
                    "metric_name": metric_name,
                    "metric_value": val,
                    "metric_unit": unit,
                    "source": f"同花顺财务摘要/{name}年报",
                })

        with Session(engine) as db:
            count = repo.batch_upsert(db, records)

        print(f"  [OK] 写入 {count} 条指标（{len(df_target)} 年 x {len(METRIC_MAP)} 项）")

    print("\n财报数据采集完成")


if __name__ == "__main__":
    raise SystemExit(LEGACY_SCRIPT_MESSAGE)
