#!/usr/bin/env python3
"""
Transform 入口脚本
用法：
    python run_transform.py stock_daily [--begin 2026-01-01] [--end 2026-04-23] [--dry-run]
    python run_transform.py announcement_raw [--dry-run]
    python run_transform.py research_report [--dry-run]
    python run_transform.py macro [--dry-run]
    python run_transform.py company [--dry-run]
    python run_transform.py all [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加 backend 根目录到 path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler.transformers import TRANSFORMER_REGISTRY


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Transform 入口")
    parser.add_argument(
        "chain",
        choices=["stock_daily", "announcement_raw", "research_report", "macro", "company", "patent", "all"],
        help="指定要执行的 transform 链",
    )
    parser.add_argument("--begin", dest="begin_date", default=None, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", dest="end_date", default=None, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="只读取不写入")
    parser.add_argument("--backend", dest="backend_root", default=None, help="backend 根目录路径")

    args = parser.parse_args()

    # 确定要执行的 chain 列表
    if args.chain == "all":
        chains = ["stock_daily", "announcement_raw", "research_report", "macro", "company", "patent"]
    else:
        chains = [args.chain]

    results = {}
    for chain in chains:
        if chain not in TRANSFORMER_REGISTRY:
            print(f"[SKIP] {chain}: 无对应 transformer（patent 禁止入库）")
            continue

        print(f"\n{'='*60}")
        print(f"[{chain}] Transform 开始")
        print(f"{'='*60}")

        try:
            cls = TRANSFORMER_REGISTRY[chain]
            transformer = cls(backend_root=args.backend_root)
            result = transformer.run(
                begin_date=args.begin_date,
                end_date=args.end_date,
                dry_run=args.dry_run,
            )

            status = result.get("status", "unknown")
            print(f"[{chain}] 状态: {status}")
            print(f"[{chain}] job_id: {result.get('job_id', 'N/A')}")
            print(f"[{chain}] staging_count: {result.get('staging_count', 0)}")

            if result.get("errors"):
                print(f"[{chain}] 错误数: {len(result['errors'])}")
                for err in result["errors"][:3]:
                    print(f"  - {err}")

            if not args.dry_run and status == "done":
                print(f"[{chain}] staging: {result.get('staging_path', 'N/A')}")
                print(f"[{chain}] manifest: {result.get('manifest_path', 'N/A')}")
                print(f"[{chain}] quality_report: {result.get('quality_report_path', 'N/A')}")

            ingest_allowed = result.get("ingest_allowed", True)
            if not ingest_allowed:
                print(f"[{chain}] ⚠️  禁止入库（patent 无对应 ingest 接口）")

            results[chain] = result

        except Exception as exc:
            print(f"[{chain}] 执行异常: {exc}")
            results[chain] = {"status": "error", "error": str(exc)}

    # 汇总输出
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    for chain, result in results.items():
        status = result.get("status", "unknown")
        count = result.get("staging_count", result.get("raw_count", "N/A"))
        print(f"  {chain}: {status} | records={count}")

    # 若有失败返回非零退出码
    if any(r.get("status") == "error" for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
