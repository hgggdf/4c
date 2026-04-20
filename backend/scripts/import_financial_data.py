"""
医药企业财报数据采集脚本
采集恒瑞医药(600276)、药明康德(603259)、爱尔眼科(300015) 近3年财务指标
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import akshare as ak
from sqlalchemy.orm import Session
from db.session import engine
from db.repository.financial_repo import FinancialDataRepository

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
    import_financial_data()
