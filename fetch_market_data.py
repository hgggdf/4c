"""
fetch_market_data.py — 从 AkShare 拉取真实 A 股日行情，写入 financial_hot 表。

运行方式（项目根目录）：
    python fetch_market_data.py

功能：
- 拉取 8 家种子公司最近 180 个交易日的真实 OHLC + 成交量/额 + 涨跌幅
- 写入 financial_hot 表（report_type="日行情"），替换已有假数据
- 单只股票失败时跳过，不中断整体流程
- 全部失败时提示检查网络，已有假数据保持不变
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import date, timedelta

# Windows UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

logging.basicConfig(level=logging.WARNING)

from app.core.database.session import SessionLocal
from app.core.database.models.financial_hot import FinancialHot

COMPANIES = [
    ("600276", "恒瑞医药"),
    ("000858", "五粮液"),
    ("300760", "迈瑞医疗"),
    ("002007", "华兰生物"),
    ("600196", "复星医药"),
    ("300347", "泰格医药"),
    ("600085", "同仁堂"),
    ("002252", "上海莱士"),
]

# 拉取最近 180 个交易日
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=270)  # 多取一些，交易日约 180 个


def fetch_one(stock_code: str, stock_name: str, max_retries: int = 3) -> list[dict] | None:
    """拉取单只股票行情，返回行列表或 None（失败）。"""
    import akshare as ak

    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=START_DATE.strftime("%Y%m%d"),
                end_date=END_DATE.strftime("%Y%m%d"),
                adjust="qfq",  # 前复权
                timeout=20,
            )
            if df is None or df.empty:
                print(f"  [{stock_name}] 返回空数据")
                return None

            rows = []
            prev_close = None
            for _, row in df.iterrows():
                trade_date = row["日期"]
                if hasattr(trade_date, "date"):
                    trade_date = trade_date.date()
                else:
                    from datetime import datetime
                    trade_date = datetime.strptime(str(trade_date), "%Y-%m-%d").date()

                close = float(row["收盘"])
                open_p = float(row["开盘"])
                high = float(row["最高"])
                low = float(row["最低"])
                volume = float(row["成交量"])   # 手
                amount = float(row["成交额"])   # 元

                # 涨跌幅：优先用原始列，否则自己算
                if "涨跌幅" in row.index:
                    change_pct = float(row["涨跌幅"]) / 100
                elif prev_close and prev_close != 0:
                    change_pct = (close - prev_close) / prev_close
                else:
                    change_pct = 0.0
                prev_close = close

                rows.append({
                    "trade_date": trade_date,
                    "open_price": open_p,
                    "close_price": close,
                    "high_price": high,
                    "low_price": low,
                    "volume": volume,
                    "amount": amount,
                    "change_pct": round(change_pct, 6),
                })
            return rows

        except Exception as exc:
            wait = 5 * (attempt + 1)
            if attempt < max_retries - 1:
                print(f"  [{stock_name}] 第{attempt+1}次失败（{exc.__class__.__name__}），{wait}s 后重试...")
                time.sleep(wait)
            else:
                print(f"  [{stock_name}] 全部重试失败：{exc.__class__.__name__}: {exc}")
                return None


def write_quotes(db, stock_code: str, rows: list[dict]) -> int:
    """删除旧日行情，写入新数据，返回写入条数。"""
    db.query(FinancialHot).filter_by(
        stock_code=stock_code, report_type="daily"
    ).delete()

    for r in rows:
        db.add(FinancialHot(
            stock_code=stock_code,
            report_date=r["trade_date"],
            report_type="daily",
            fiscal_year=r["trade_date"].year,
            trade_date=r["trade_date"],
            open_price=r["open_price"],
            close_price=r["close_price"],
            high_price=r["high_price"],
            low_price=r["low_price"],
            volume=r["volume"],
            amount=r["amount"],
            change_pct=r["change_pct"],
            query_count=0,
        ))
    db.flush()
    return len(rows)


def main():
    print(f"开始拉取真实行情数据（{START_DATE} ~ {END_DATE}）...\n")

    success_count = 0
    fail_codes = []
    total_rows = 0

    db = SessionLocal()
    try:
        for stock_code, stock_name in COMPANIES:
            print(f"  正在拉取 {stock_name}({stock_code})...", end=" ", flush=True)
            rows = fetch_one(stock_code, stock_name)

            if rows:
                n = write_quotes(db, stock_code, rows)
                print(f"✓ {n} 条")
                success_count += 1
                total_rows += n
            else:
                print("✗ 跳过（保留原有数据）")
                fail_codes.append(f"{stock_name}({stock_code})")

            # 礼貌间隔，避免被限速
            time.sleep(1.5)

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"\n❌ 写入异常：{exc}")
        raise
    finally:
        db.close()

    print(f"\n完成：{success_count}/{len(COMPANIES)} 家成功，共写入 {total_rows} 条真实行情。")
    if fail_codes:
        print(f"失败：{', '.join(fail_codes)}")
        print("提示：失败的公司保留了原有的随机行情数据，量价分析仍可正常使用。")
        if success_count == 0:
            print("\n全部失败，可能原因：")
            print("  1. 网络无法访问东方财富（push2his.eastmoney.com）")
            print("  2. 代理/防火墙拦截")
            print("  3. AkShare 接口变更（尝试 pip install -U akshare）")


if __name__ == "__main__":
    main()
