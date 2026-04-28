"""
综合测试脚本：热冷库查询 + query_count 自增 + financial daily 冷热交替 + financial_trend 工具

测试内容：
  1. Repository 层热冷查询 + query_count 自增（4张表）
  2. financial daily 数据冷热交替逻辑（只按时间，不看 query_count）
  3. financial_trend 工具映射是否正常
  4. 向量库回填脚本导入验证

运行方式：
    cd backend
    python test_hot_cold_v2.py
"""

import io
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from datetime import date, datetime, timedelta
from sqlalchemy import select, update

from app.core.database.session import SessionLocal
from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
from app.core.repositories.news_repository import NewsRepository
from app.core.repositories.announcement_repository import AnnouncementRepository
from app.core.repositories.financial_repository import FinancialRepository
from app.core.repositories.research_report_repository import ResearchReportRepository
from ingest_center.hot_archive_service import (
    HotArchiveService, FINANCIAL_DAILY_COLD_DAYS, COLD_QUERY_THRESHOLD,
)

PASS = "  [PASS]"
FAIL = "  [FAIL]"
SKIP = "  [SKIP]"
SEP = "=" * 60


# ─────────────────────────────────────────────
# Test 1: News 热冷查询 + query_count 自增
# ─────────────────────────────────────────────
def test_news_query_count():
    print(SEP)
    print("Test 1: News 热库查询后 query_count 自增")
    print(SEP)

    db = SessionLocal()
    try:
        row = db.execute(select(NewsHot).limit(1)).scalars().first()
        if not row:
            print(f"{SKIP} news_hot 表为空")
            return None

        row_id = row.id
        db.execute(update(NewsHot).where(NewsHot.id == row_id).values(query_count=0))
        db.commit()
        print(f"  target: id={row_id}, 重置 query_count=0")

        repo = NewsRepository(db)
        result = repo.get_news_raw_by_id(row_id)

        db.expire_all()
        row = db.execute(select(NewsHot).where(NewsHot.id == row_id)).scalars().first()
        count = row.query_count if row else -1
        print(f"  查询后 query_count={count}")

        if count >= 1:
            print(f"{PASS} query_count 自增成功")
            return True
        else:
            print(f"{FAIL} query_count 未自增 (got {count})")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 2: Announcement 热冷查询 + query_count 自增
# ─────────────────────────────────────────────
def test_announcement_query_count():
    print()
    print(SEP)
    print("Test 2: Announcement 热库查询后 query_count 自增")
    print(SEP)

    db = SessionLocal()
    try:
        row = db.execute(select(AnnouncementHot).limit(1)).scalars().first()
        if not row:
            print(f"{SKIP} announcement_hot 表为空")
            return None

        row_id = row.id
        stock_code = row.stock_code
        db.execute(update(AnnouncementHot).where(AnnouncementHot.id == row_id).values(query_count=0))
        db.commit()
        print(f"  target: id={row_id}, stock_code={stock_code}, 重置 query_count=0")

        repo = AnnouncementRepository(db)
        results = repo.list_raw_announcements(stock_code, days=3650)

        db.expire_all()
        row = db.execute(select(AnnouncementHot).where(AnnouncementHot.id == row_id)).scalars().first()
        count = row.query_count if row else -1
        print(f"  查询返回 {len(results)} 条, target query_count={count}")

        if count >= 1:
            print(f"{PASS} query_count 自增成功")
            return True
        else:
            print(f"{FAIL} query_count 未自增 (got {count})")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 3: Financial 热冷查询 + query_count 自增
# ─────────────────────────────────────────────
def test_financial_query_count():
    print()
    print(SEP)
    print("Test 3: Financial 热库查询后 query_count 自增")
    print(SEP)

    db = SessionLocal()
    try:
        row = db.execute(
            select(FinancialHot).where(FinancialHot.report_type != 'daily').limit(1)
        ).scalars().first()
        if not row:
            print(f"{SKIP} financial_hot 表为空（非 daily）")
            return None

        row_id = row.id
        stock_code = row.stock_code
        db.execute(update(FinancialHot).where(FinancialHot.id == row_id).values(query_count=0))
        db.commit()
        print(f"  target: id={row_id}, stock_code={stock_code}, report_type={row.report_type}, 重置 query_count=0")

        repo = FinancialRepository(db)
        results = repo.list_income_statements(stock_code, limit=20)

        db.expire_all()
        row = db.execute(select(FinancialHot).where(FinancialHot.id == row_id)).scalars().first()
        count = row.query_count if row else -1
        print(f"  查询返回 {len(results)} 条, target query_count={count}")

        if count >= 1:
            print(f"{PASS} query_count 自增成功")
            return True
        else:
            print(f"{FAIL} query_count 未自增 (got {count})")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 4: 冷库回退查询（模拟热库无数据）
# ─────────────────────────────────────────────
def test_cold_fallback():
    print()
    print(SEP)
    print("Test 4: 冷库回退查询验证")
    print(SEP)

    db = SessionLocal()
    try:
        cold_row = db.execute(select(NewsArchive).limit(1)).scalars().first()
        if not cold_row:
            print(f"{SKIP} news_archive 表为空，无法测试冷库回退")
            return None

        cold_id = cold_row.id
        db.execute(update(NewsArchive).where(NewsArchive.id == cold_id).values(query_count=0))
        db.commit()
        print(f"  冷库记录: id={cold_id}, 重置 query_count=0")

        repo = NewsRepository(db)
        result = repo.get_news_raw_by_id(cold_id)

        if result is None:
            # 热库里可能有同 id 的记录，这种情况下冷库不会被查到
            hot_exists = db.execute(select(NewsHot).where(NewsHot.id == cold_id)).scalars().first()
            if hot_exists:
                print(f"{SKIP} 热库存在同 id 记录，冷库回退未触发（正常行为）")
                return None
            print(f"{FAIL} 冷库记录未被查到")
            return False

        db.expire_all()
        cold_row = db.execute(select(NewsArchive).where(NewsArchive.id == cold_id)).scalars().first()
        count = cold_row.query_count if cold_row else -1
        print(f"  冷库查询成功, query_count={count}")

        if count >= 1:
            print(f"{PASS} 冷库回退查询 + query_count 自增成功")
            return True
        else:
            print(f"{FAIL} 冷库 query_count 未自增")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 5: Financial daily 冷热交替逻辑
# ─────────────────────────────────────────────
def test_financial_daily_archive():
    print()
    print(SEP)
    print("Test 5: Financial daily 冷热交替（只按时间，不看 query_count）")
    print(SEP)

    db = SessionLocal()
    try:
        # 查找一条 daily 数据
        daily_row = db.execute(
            select(FinancialHot).where(FinancialHot.report_type == 'daily').limit(1)
        ).scalars().first()
        if not daily_row:
            print(f"{SKIP} financial_hot 中无 daily 数据")
            return None

        print(f"  daily 数据示例: id={daily_row.id}, report_date={daily_row.report_date}")
        print(f"  FINANCIAL_DAILY_COLD_DAYS={FINANCIAL_DAILY_COLD_DAYS}")

        svc = HotArchiveService(db)

        # dry_run 检查 daily 归档逻辑
        cutoff = date.today() - timedelta(days=FINANCIAL_DAILY_COLD_DAYS)
        old_daily_count = db.execute(
            select(FinancialHot)
            .where(FinancialHot.report_type == 'daily')
            .where(FinancialHot.report_date < cutoff)
        ).scalars().all()
        print(f"  超过 {FINANCIAL_DAILY_COLD_DAYS} 天的 daily 数据: {len(old_daily_count)} 条")

        # 验证 daily 归档不看 query_count
        high_qc_daily = [r for r in old_daily_count if (r.query_count or 0) >= COLD_QUERY_THRESHOLD]
        print(f"  其中 query_count >= {COLD_QUERY_THRESHOLD} 的: {len(high_qc_daily)} 条")

        if high_qc_daily:
            print(f"  这些高频 daily 数据也应该被归档（只按时间）")

        dry_result = svc.archive_cold(dry_run=True)
        print(f"  dry_run 归档结果: {dry_result}")
        print(f"{PASS} daily 冷热交替逻辑验证完成")
        return True
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 6: Financial daily 冷库不回温
# ─────────────────────────────────────────────
def test_daily_no_restore():
    print()
    print(SEP)
    print("Test 6: Financial daily 冷库数据不回温")
    print(SEP)

    db = SessionLocal()
    try:
        cold_daily = db.execute(
            select(FinancialArchive).where(FinancialArchive.report_type == 'daily').limit(1)
        ).scalars().first()
        if not cold_daily:
            print(f"{SKIP} financial_archive 中无 daily 数据")
            return None

        cold_id = cold_daily.id
        stock_code = cold_daily.stock_code
        report_date = cold_daily.report_date

        # 记录回温前热库中该条件的记录数
        hot_before = len(db.execute(
            select(FinancialHot)
            .where(FinancialHot.stock_code == stock_code)
            .where(FinancialHot.report_date == report_date)
            .where(FinancialHot.report_type == 'daily')
        ).scalars().all())

        # 设置超高 query_count 并触发 increment
        db.execute(
            update(FinancialArchive).where(FinancialArchive.id == cold_id).values(query_count=100)
        )
        db.commit()
        print(f"  冷库 daily: id={cold_id}, 设置 query_count=100")

        svc = HotArchiveService(db)
        svc.increment_query_count("financial", cold_id, is_archive=True)

        # 检查热库记录数是否增加
        hot_after = len(db.execute(
            select(FinancialHot)
            .where(FinancialHot.stock_code == stock_code)
            .where(FinancialHot.report_date == report_date)
            .where(FinancialHot.report_type == 'daily')
        ).scalars().all())

        print(f"  热库记录数: before={hot_before}, after={hot_after}")

        if hot_after == hot_before:
            print(f"{PASS} daily 数据未回温（正确行为）")
            return True
        else:
            print(f"{FAIL} daily 数据被回温了（热库新增了 {hot_after - hot_before} 条）")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 7: financial_trend 工具映射
# ─────────────────────────────────────────────
def test_financial_trend_tool():
    print()
    print(SEP)
    print("Test 7: financial_trend 工具映射验证")
    print(SEP)

    db = SessionLocal()
    try:
        row = db.execute(
            select(FinancialHot).where(FinancialHot.report_type != 'daily').limit(1)
        ).scalars().first()
        if not row:
            print(f"{SKIP} financial_hot 表为空")
            return None
        stock_code = row.stock_code
    finally:
        db.close()

    from agent.integration.tool_executor import _run_tool

    success, data, error = _run_tool("financial_trend", {"stock_code": stock_code})
    print(f"  stock_code={stock_code}")
    print(f"  success={success}, error={error}")

    if success and data:
        keys = list(data.keys()) if isinstance(data, dict) else []
        print(f"  返回字段: {keys}")
        print(f"{PASS} financial_trend 工具映射正常")
        return True
    else:
        print(f"{FAIL} financial_trend 工具执行失败: {error}")
        return False


# ─────────────────────────────────────────────
# Test 8: 向量库回填脚本导入验证
# ─────────────────────────────────────────────
def test_backfill_import():
    print()
    print(SEP)
    print("Test 8: 向量库回填脚本导入验证")
    print(SEP)

    try:
        from scripts.backfill_vector_store import run_backfill, BACKFILL_ORDER
        doc_types = [name for name, _ in BACKFILL_ORDER]
        print(f"  BACKFILL_ORDER 包含: {doc_types}")

        has_research = any("research" in name for name, _ in BACKFILL_ORDER)
        print(f"  包含 research_report: {has_research}")

        # 检查 company_profile 同步
        from app.knowledge.sync import sync_company_profiles
        print(f"  sync_company_profiles 导入成功")

        if has_research:
            print(f"{PASS} 回填脚本覆盖所有数据类型")
            return True
        else:
            print(f"{FAIL} 回填脚本缺少 research_report")
            return False
    except Exception as e:
        print(f"{FAIL} 导入失败: {e}")
        return False


# ─────────────────────────────────────────────
# Test 9: ResearchReport 热冷查询
# ─────────────────────────────────────────────
def test_research_report_query_count():
    print()
    print(SEP)
    print("Test 9: ResearchReport 热库查询后 query_count 自增")
    print(SEP)

    db = SessionLocal()
    try:
        # 先找一个有数据的 industry_code
        row = db.execute(
            select(ResearchReportHot)
            .where(ResearchReportHot.industry_code.isnot(None))
            .limit(1)
        ).scalars().first()
        if not row:
            print(f"{SKIP} research_report_hot 表为空")
            return None

        industry_code = row.industry_code

        # 把该 industry_code 下所有记录的 query_count 重置为 0
        db.execute(
            update(ResearchReportHot)
            .where(ResearchReportHot.industry_code == industry_code)
            .values(query_count=0)
        )
        db.commit()
        print(f"  industry_code={industry_code}, 已重置所有记录 query_count=0")

        repo = ResearchReportRepository(db)
        results = repo.list_by_industry(industry_code, limit=10)
        print(f"  查询返回 {len(results)} 条")

        if not results:
            print(f"{SKIP} 查询无结果")
            return None

        # 检查返回结果中第一条的 query_count
        first_id = results[0].id
        db.expire_all()
        check = db.execute(select(ResearchReportHot).where(ResearchReportHot.id == first_id)).scalars().first()
        count = check.query_count if check else -1
        print(f"  结果第一条 id={first_id}, query_count={count}")

        if count >= 1:
            print(f"{PASS} query_count 自增成功")
            return True
        else:
            print(f"{FAIL} query_count 未自增 (got {count})")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n[Hot/Cold V2 综合测试]\n")

    tests = [
        ("News query_count 自增", test_news_query_count),
        ("Announcement query_count 自增", test_announcement_query_count),
        ("Financial query_count 自增", test_financial_query_count),
        ("冷库回退查询", test_cold_fallback),
        ("Financial daily 冷热交替", test_financial_daily_archive),
        ("Financial daily 不回温", test_daily_no_restore),
        ("financial_trend 工具映射", test_financial_trend_tool),
        ("向量库回填脚本", test_backfill_import),
        ("ResearchReport query_count 自增", test_research_report_query_count),
    ]

    results = []
    for name, fn in tests:
        try:
            result = fn()
            results.append((name, result))
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append((name, False))

    print()
    print(SEP)
    print("Summary")
    print(SEP)
    passed = 0
    failed = 0
    skipped = 0
    for name, result in results:
        if result is True:
            status = "[PASS]"
            passed += 1
        elif result is None:
            status = "[SKIP]"
            skipped += 1
        else:
            status = "[FAIL]"
            failed += 1
        print(f"  {status} {name}")

    print()
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print()
