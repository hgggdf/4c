"""
股票数据导入脚本
从 AKShare 批量导入股票历史数据到 MySQL
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import engine
from app.data.akshare_client import StockDataProvider
from app.data.company_data_store import CompanyDataStore
from app.data.pharma_company_registry import list_pharma_companies
from db.repository.stock_repo import StockDailyRepository

# 默认导入的股票列表（可扩展）
DEFAULT_STOCKS = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    "600036",  # 招商银行
    "300750",  # 宁德时代
    "002594",  # 比亚迪
    "000002",  # 万科A
    "600000",  # 浦发银行
    "601318",  # 中国平安
    "600276",  # 恒瑞医药
    "300015",  # 爱尔眼科
]

PHARMA_STOCKS = [item["symbol"] for item in list_pharma_companies()]


def import_stock_history(stock_code: str, days: int = 365) -> None:
    """导入单个股票的历史数据"""
    provider = StockDataProvider()
    repo = StockDailyRepository()

    print(f"正在导入 {stock_code} 最近 {days} 天的数据...")

    try:
        data = provider.get_kline(stock_code, days)

        with Session(engine) as db:
            repo.upsert_many(db, stock_code, data)

        print(f"[OK] {stock_code} 导入成功，共 {len(data)} 条记录")
    except Exception as e:
        print(f"[FAIL] {stock_code} 导入失败: {e}")


def import_all_stocks(days: int = 365) -> None:
    """批量导入所有默认股票的历史数据"""
    print(f"开始批量导入 {len(DEFAULT_STOCKS)} 只股票的历史数据...")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for stock_code in DEFAULT_STOCKS:
        try:
            import_stock_history(stock_code, days)
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {stock_code} 导入失败: {e}")
            fail_count += 1

    print("=" * 60)
    print(f"导入完成: 成功 {success_count} 只，失败 {fail_count} 只")


def import_company_dataset(stock_code: str, days: int = 180) -> None:
    provider = StockDataProvider()
    store = CompanyDataStore()

    print(f"正在采集 {stock_code} 的多源公司数据...")
    try:
        dataset = provider.collect_company_dataset(stock_code, history_days=days)
        summary = store.save_company_dataset(dataset)
        print(f"[OK] {stock_code} 数据采集完成，更新时间 {summary.get('collected_at')}")
    except Exception as exc:
        print(f"[FAIL] {stock_code} 数据采集失败: {exc}")


def import_all_pharma_companies(days: int = 180) -> None:
    print(f"开始采集 {len(PHARMA_STOCKS)} 家医药公司多源数据...")
    print("=" * 60)
    for stock_code in PHARMA_STOCKS:
        import_company_dataset(stock_code, days)
    print("=" * 60)
    print("医药公司数据采集完成")


def check_data_status() -> None:
    """检查数据库中的股票数据状态"""
    from sqlalchemy import text

    with Session(engine) as db:
        result = db.execute(text("""
            SELECT
                stock_code,
                COUNT(*) as record_count,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date
            FROM stock_daily
            GROUP BY stock_code
            ORDER BY stock_code
        """))

        print("\n数据库中的股票数据状态:")
        print("=" * 80)
        print(f"{'股票代码':<12} {'记录数':<10} {'最早日期':<15} {'最新日期':<15}")
        print("-" * 80)

        for row in result:
            print(f"{row.stock_code:<12} {row.record_count:<10} {row.earliest_date} {row.latest_date}")

        print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="股票数据导入工具")
    parser.add_argument("--stock", type=str, help="导入指定股票代码")
    parser.add_argument("--days", type=int, default=365, help="导入天数（默认365天）")
    parser.add_argument("--all", action="store_true", help="导入所有默认股票")
    parser.add_argument("--company", type=str, help="采集指定公司多源数据")
    parser.add_argument("--pharma-all", action="store_true", help="采集 20 家医药公司全部多源数据")
    parser.add_argument("--status", action="store_true", help="查看数据状态")

    args = parser.parse_args()

    if args.status:
        check_data_status()
    elif args.company:
        import_company_dataset(args.company, args.days)
    elif args.pharma_all:
        import_all_pharma_companies(args.days)
    elif args.stock:
        import_stock_history(args.stock, args.days)
    elif args.all:
        import_all_stocks(args.days)
    else:
        print("请指定操作: --stock <代码> | --all | --company <代码> | --pharma-all | --status")
        print("示例:")
        print("  python import_stock_data.py --stock 600519 --days 180")
        print("  python import_stock_data.py --all")
        print("  python import_stock_data.py --company 600276 --days 180")
        print("  python import_stock_data.py --pharma-all --days 180")
        print("  python import_stock_data.py --status")
