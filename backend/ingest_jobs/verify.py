#!/usr/bin/env python3
"""
verify.py
入库验收脚本

检查数据库中的数据，确认入库成功

验收项目：
1. company_master 是否有 ≥N 家
2. stock_daily_hot 是否有记录
3. announcement_raw_hot 是否有近 30 天公告
4. news_raw_hot 是否有研报类型记录
5. macro_indicator_hot 是否有宏观指标记录

使用方式：
python verify.py                    # 检查所有项
python verify.py --check company    # 只检查 company
python verify.py --min-company 10   # 指定最小公司数
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest_jobs import get_config


# 默认验收标准
DEFAULT_MIN = {
    "company": 10,
    "stock_daily": 10,
    "announcement": 10,
    "research_report": 5,
    "macro": 5,
}


def verify(config: "IngestConfig", checks: dict) -> dict:
    """
    执行验收检查
    通过 SQL 查询数据库
    """
    results = {}

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        return {"error": "sqlalchemy 未安装，无法连接数据库"}

    try:
        # 优先使用 MySQL，如果配置有 database_url_override
        database_url = getattr(config, "_database_url_override", None)
        if not database_url:
            database_url = config.database_url
    except Exception:
        # fallback: 读取 .env
        database_url = None

    if not database_url:
        results["company"] = {"passed": False, "error": "未配置数据库连接"}
        return results

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            # 1. company_master 检查
            if checks.get("company"):
                min_count = checks["company"].get("min", DEFAULT_MIN["company"])
                row = conn.execute(text("SELECT COUNT(*) as cnt FROM company_master")).fetchone()
                count = row[0] if row else 0
                results["company"] = {
                    "passed": count >= min_count,
                    "actual": count,
                    "min_required": min_count,
                    "table": "company_master",
                }

            # 2. stock_daily_hot 检查
            if checks.get("stock_daily"):
                min_count = checks["stock_daily"].get("min", DEFAULT_MIN["stock_daily"])
                row = conn.execute(text("SELECT COUNT(*) as cnt FROM stock_daily_hot")).fetchone()
                count = row[0] if row else 0
                results["stock_daily"] = {
                    "passed": count >= min_count,
                    "actual": count,
                    "min_required": min_count,
                    "table": "stock_daily_hot",
                }

            # 3. announcement_raw_hot 近 30 天检查
            if checks.get("announcement"):
                min_count = checks["announcement"].get("min", DEFAULT_MIN["announcement"])
                thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
                row = conn.execute(
                    text("SELECT COUNT(*) as cnt FROM announcement_raw_hot WHERE publish_date >= :date"),
                    {"date": thirty_days_ago},
                ).fetchone()
                count = row[0] if row else 0
                results["announcement"] = {
                    "passed": count >= min_count,
                    "actual": count,
                    "min_required": min_count,
                    "table": "announcement_raw_hot",
                    "note": f"近30天 ({thirty_days_ago} 至今)",
                }

            # 4. news_raw_hot 研报类型检查
            if checks.get("research_report"):
                min_count = checks["research_report"].get("min", DEFAULT_MIN["research_report"])
                row = conn.execute(
                    text("SELECT COUNT(*) as cnt FROM news_raw_hot WHERE news_type LIKE '%research_report%'")
                ).fetchone()
                count = row[0] if row else 0
                results["research_report"] = {
                    "passed": count >= min_count,
                    "actual": count,
                    "min_required": min_count,
                    "table": "news_raw_hot",
                    "note": "news_type LIKE '%research_report%'",
                }

            # 5. macro_indicator_hot 检查
            if checks.get("macro"):
                min_count = checks["macro"].get("min", DEFAULT_MIN["macro"])
                row = conn.execute(text("SELECT COUNT(*) as cnt FROM macro_indicator_hot")).fetchone()
                count = row[0] if row else 0
                results["macro"] = {
                    "passed": count >= min_count,
                    "actual": count,
                    "min_required": min_count,
                    "table": "macro_indicator_hot",
                }

    except Exception as exc:
        for key in checks:
            results[key] = {"passed": False, "error": str(exc)}
        results["_connection_error"] = str(exc)

    return results


def main():
    parser = argparse.ArgumentParser(description="入库验收脚本")
    parser.add_argument("--check", dest="check_only", default=None, help="只检查指定项")
    parser.add_argument("--min-company", dest="min_company", type=int, default=None)
    parser.add_argument("--min-stock-daily", dest="min_stock_daily", type=int, default=None)
    parser.add_argument("--min-announcement", dest="min_announcement", type=int, default=None)
    parser.add_argument("--min-research-report", dest="min_research_report", type=int, default=None)
    parser.add_argument("--min-macro", dest="min_macro", type=int, default=None)
    parser.add_argument("--backend", dest="backend_root", default=None)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.backend_root:
        import ingest_jobs.config as _cfg
        _cfg._config = None

    config = get_config()

    # 构建 checks
    all_checks = {
        "company": {"min": args.min_company or DEFAULT_MIN["company"]} if args.check_only in (None, "company") else None,
        "stock_daily": {"min": args.min_stock_daily or DEFAULT_MIN["stock_daily"]} if args.check_only in (None, "stock_daily") else None,
        "announcement": {"min": args.min_announcement or DEFAULT_MIN["announcement"]} if args.check_only in (None, "announcement") else None,
        "research_report": {"min": args.min_research_report or DEFAULT_MIN["research_report"]} if args.check_only in (None, "research_report") else None,
        "macro": {"min": args.min_macro or DEFAULT_MIN["macro"]} if args.check_only in (None, "macro") else None,
    }
    checks = {k: v for k, v in all_checks.items() if v is not None}

    results = verify(config, checks)

    print(f"\n{'='*50}")
    print("入库验收结果")
    print(f"{'='*50}")

    all_passed = True
    for name, result in results.items():
        if name.startswith("_"):
            continue
        passed = result.get("passed", False)
        symbol = "✅" if passed else "❌"
        actual = result.get("actual", "N/A")
        min_req = result.get("min_required", "N/A")
        table = result.get("table", "")
        note = result.get("note", "")

        print(f"{symbol} {name}: {actual}/{min_req} ({table})")
        if note:
            print(f"   {note}")
        if not passed and result.get("error"):
            print(f"   error: {result['error']}")

        if not passed:
            all_passed = False

    if results.get("_connection_error"):
        print(f"\n⚠️  数据库连接失败: {results['_connection_error']}")
        all_passed = False

    print(f"\n{'='*50}")
    print(f"验收: {'全部通过 ✅' if all_passed else '存在失败 ❌'}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
