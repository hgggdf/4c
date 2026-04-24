#!/usr/bin/env python3
"""
run_all.py
总控脚本

按固定顺序执行 5 条链：
company → stock_daily → announcement_raw → research_report → macro

对应关系：
  company        → run_company.run_company       → data_category="company"
  stock_daily   → run_market.run_market          → data_category="stock_daily"
  announcement_raw → run_announcement.run_announcement → data_category="announcement_raw"
  research_report → run_report.run_report        → data_category="research_report"
  macro         → run_macro.run_macro           → data_category="macro"

专利链（patent）不执行（禁止入库）

每条链：
- 有 manifest 时执行
- 无 manifest 时跳过（不报错）
- 单条失败时其余继续
- 最终输出 summary
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest_jobs import ManifestLoader


def main():
    parser = argparse.ArgumentParser(description="ingest_jobs 总控脚本")
    parser.add_argument("--dry-run", action="store_true", help="只校验不写入")
    parser.add_argument("--backend", dest="backend_root", default=None, help="backend 根目录")
    parser.add_argument(
        "--skip",
        dest="skip_chains",
        default="",
        help="跳过的链，逗号分隔，如: company,micro",
    )

    args = parser.parse_args()

    if args.backend_root:
        import ingest_jobs.config as _cfg
        _cfg._config = None

    # 导入各链执行函数
    from . import run_company, run_market, run_announcement, run_report, run_macro

    # 固定顺序（patent 除外）
    # data_category 值必须与 ManifestLoader 返回的 manifest.data_category 完全一致
    chain_order = [
        ("company", run_company.run_company),
        ("stock_daily", run_market.run_market),
        ("announcement_raw", run_announcement.run_announcement),
        ("research_report", run_report.run_report),
        ("macro", run_macro.run_macro),
    ]

    skip_set = set(args.skip_chains.split(",")) if args.skip_chains else set()

    manifest_loader = ManifestLoader()
    results = {}
    total_written = 0
    total_failed = 0

    for chain_name, chain_func in chain_order:
        if chain_name in skip_set:
            print(f"[{chain_name}] 跳过（--skip）")
            results[chain_name] = {"status": "skipped", "reason": "--skip"}
            continue

        # 检查是否有待处理的 manifest
        manifests = manifest_loader.list_pending_manifests()
        manifest = next((m for m in manifests if m.data_category == chain_name), None)

        if manifest is None:
            print(f"[{chain_name}] ⏭️  无待处理 manifest，跳过")
            results[chain_name] = {"status": "skipped", "reason": "no manifest"}
            continue

        print(f"\n[{chain_name}] ▶️  执行")
        print(f"[{chain_name}]   job_id: {manifest.job_id}")

        try:
            result = chain_func(job_id=manifest.job_id, dry_run=args.dry_run)
            results[chain_name] = result

            status = "✅" if result.get("success") else "❌"
            print(f"[{chain_name}] {status} {result.get('status', 'unknown')}")
            print(f"[{chain_name}]   written: {result.get('written_count', 0)}")
            if result.get("error"):
                print(f"[{chain_name}]   error: {result.get('error')}")

            if result.get("success"):
                total_written += result.get("written_count", 0)
            else:
                total_failed += 1

        except Exception as exc:
            print(f"[{chain_name}] ❌ 执行异常: {exc}")
            results[chain_name] = {"status": "error", "error": str(exc)}
            total_failed += 1

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    for chain_name, result in results.items():
        status = result.get("status", "unknown")
        written = result.get("written_count", "N/A")
        print(f"  {chain_name}: {status} | written={written}")

    print(f"\n总计：written={total_written}, failed={total_failed}")

    if args.dry_run:
        print("\n[DRY-RUN 模式，未实际写入]")

    # 返回非零退出码表示有失败
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
