"""
测试脚本：验证冷库回退阈值 COLD_FALLBACK_THRESHOLD = 5

测试逻辑：
  1. 热库结果 >= 5 条时，不查冷库
  2. 热库结果 < 5 条时，从冷库补充
  3. 热库结果 0 条时，全部从冷库返回

运行方式：
    cd backend
    python test_cold_fallback_threshold.py
"""

import io
import sys
from pathlib import Path
from unittest.mock import patch

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func

from app.core.database.session import SessionLocal
from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
from app.core.repositories.base import BaseRepository
from app.core.repositories.news_repository import NewsRepository
from app.core.repositories.announcement_repository import AnnouncementRepository
from app.core.repositories.financial_repository import FinancialRepository

PASS = "  [PASS]"
FAIL = "  [FAIL]"
SKIP = "  [SKIP]"
SEP = "=" * 60


# ─────────────────────────────────────────────
# Test 0: 验证阈值常量
# ─────────────────────────────────────────────
def test_threshold_value():
    print(SEP)
    print("Test 0: COLD_FALLBACK_THRESHOLD 值验证")
    print(SEP)

    val = BaseRepository.COLD_FALLBACK_THRESHOLD
    print(f"  COLD_FALLBACK_THRESHOLD = {val}")

    if val == 5:
        print(f"{PASS} 阈值为 5")
        return True
    else:
        print(f"{FAIL} 阈值不是 5，当前为 {val}")
        return False


# ─────────────────────────────────────────────
# Test 1: 热库结果充足（>= 5）时不查冷库
# ─────────────────────────────────────────────
def test_hot_sufficient_no_cold():
    print()
    print(SEP)
    print("Test 1: 热库结果 >= 5 条时，不查冷库")
    print(SEP)

    db = SessionLocal()
    try:
        # 找一个热库数据充足的 stock_code
        row = db.execute(
            select(AnnouncementHot.stock_code, func.count(AnnouncementHot.id).label("cnt"))
            .group_by(AnnouncementHot.stock_code)
            .having(func.count(AnnouncementHot.id) >= 10)
            .limit(1)
        ).first()
        if not row:
            print(f"{SKIP} 找不到热库 >= 10 条公告的 stock_code")
            return None

        stock_code, hot_count = row
        print(f"  stock_code={stock_code}, 热库公告数={hot_count}")

        repo = AnnouncementRepository(db)

        # 用 patch 监控冷库是否被查询
        original_scalars_all = BaseRepository.scalars_all
        cold_called = {"value": False}

        def patched_scalars_all(self, stmt):
            stmt_str = str(stmt)
            if "announcement_archive" in stmt_str.lower():
                cold_called["value"] = True
            return original_scalars_all(self, stmt)

        with patch.object(BaseRepository, "scalars_all", patched_scalars_all):
            results = repo.list_raw_announcements(stock_code, days=3650)

        print(f"  查询返回 {len(results)} 条")
        print(f"  冷库被查询: {cold_called['value']}")

        if not cold_called["value"] and len(results) >= 5:
            print(f"{PASS} 热库充足时未查冷库")
            return True
        elif cold_called["value"]:
            print(f"{FAIL} 热库充足但仍查了冷库")
            return False
        else:
            print(f"{SKIP} 热库结果不足 5 条，无法验证")
            return None
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 2: 热库结果不足（< 5）时查冷库补充
# ─────────────────────────────────────────────
def test_hot_insufficient_cold_fallback():
    print()
    print(SEP)
    print("Test 2: 热库结果 < 5 条时，查冷库补充")
    print(SEP)

    db = SessionLocal()
    try:
        # 检查冷库是否有数据
        cold_count = db.execute(select(func.count(AnnouncementArchive.id))).scalar() or 0
        if cold_count == 0:
            # 尝试其他表
            cold_count = db.execute(select(func.count(FinancialArchive.id))).scalar() or 0
            if cold_count == 0:
                cold_count = db.execute(select(func.count(NewsArchive.id))).scalar() or 0
                if cold_count == 0:
                    print(f"{SKIP} 所有冷库表均为空，无法测试冷库回退")
                    return None

        # 用 financial 表测试（冷库有数据）
        # 找一个热库数据少于 5 条的 stock_code
        fin_cold_count = db.execute(select(func.count(FinancialArchive.id))).scalar() or 0
        if fin_cold_count > 0:
            print(f"  financial_archive 有 {fin_cold_count} 条数据")

            # 找一个只在冷库有数据、热库数据少的 stock_code
            cold_codes = db.execute(
                select(FinancialArchive.stock_code)
                .where(FinancialArchive.report_type != 'daily')
                .group_by(FinancialArchive.stock_code)
                .limit(10)
            ).scalars().all()

            target_code = None
            for code in cold_codes:
                hot_cnt = db.execute(
                    select(func.count(FinancialHot.id))
                    .where(FinancialHot.stock_code == code)
                    .where(FinancialHot.report_type != 'daily')
                ).scalar() or 0
                if hot_cnt < 5:
                    target_code = code
                    print(f"  找到 stock_code={code}, 热库非daily={hot_cnt} 条")
                    break

            if target_code:
                repo = FinancialRepository(db)

                original_scalars_all = BaseRepository.scalars_all
                cold_called = {"value": False}

                def patched_scalars_all(self, stmt):
                    stmt_str = str(stmt)
                    if "financial_archive" in stmt_str.lower():
                        cold_called["value"] = True
                    return original_scalars_all(self, stmt)

                with patch.object(BaseRepository, "scalars_all", patched_scalars_all):
                    results = repo.list_income_statements(target_code, limit=10)

                print(f"  查询返回 {len(results)} 条")
                print(f"  冷库被查询: {cold_called['value']}")

                if cold_called["value"]:
                    print(f"{PASS} 热库不足时查了冷库补充")
                    return True
                else:
                    print(f"{FAIL} 热库不足但未查冷库")
                    return False

        # 如果 financial 冷库没有合适数据，用 announcement 测试
        ann_cold_count = db.execute(select(func.count(AnnouncementArchive.id))).scalar() or 0
        if ann_cold_count > 0:
            print(f"  announcement_archive 有 {ann_cold_count} 条数据")

            cold_codes = db.execute(
                select(AnnouncementArchive.stock_code)
                .group_by(AnnouncementArchive.stock_code)
                .limit(10)
            ).scalars().all()

            for code in cold_codes:
                hot_cnt = db.execute(
                    select(func.count(AnnouncementHot.id))
                    .where(AnnouncementHot.stock_code == code)
                ).scalar() or 0
                if hot_cnt < 5:
                    print(f"  找到 stock_code={code}, 热库公告={hot_cnt} 条")

                    repo = AnnouncementRepository(db)
                    original_scalars_all = BaseRepository.scalars_all
                    cold_called = {"value": False}

                    def patched_scalars_all(self, stmt):
                        stmt_str = str(stmt)
                        if "announcement_archive" in stmt_str.lower():
                            cold_called["value"] = True
                        return original_scalars_all(self, stmt)

                    with patch.object(BaseRepository, "scalars_all", patched_scalars_all):
                        results = repo.list_raw_announcements(code, days=3650)

                    print(f"  查询返回 {len(results)} 条")
                    print(f"  冷库被查询: {cold_called['value']}")

                    if cold_called["value"]:
                        print(f"{PASS} 热库不足时查了冷库补充")
                        return True
                    else:
                        print(f"{FAIL} 热库不足但未查冷库")
                        return False

        print(f"{SKIP} 找不到热库 < 5 条且冷库有数据的 stock_code")
        return None
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 3: 边界值测试 — 恰好 5 条不查冷库
# ─────────────────────────────────────────────
def test_boundary_exactly_5():
    print()
    print(SEP)
    print("Test 3: 边界值 — 热库恰好 5 条时不查冷库")
    print(SEP)

    db = SessionLocal()
    try:
        # 找一个热库恰好有 5 条以上公告的 stock_code
        rows = db.execute(
            select(AnnouncementHot.stock_code, func.count(AnnouncementHot.id).label("cnt"))
            .group_by(AnnouncementHot.stock_code)
            .having(func.count(AnnouncementHot.id) >= 5)
            .order_by(func.count(AnnouncementHot.id).asc())
            .limit(1)
        ).first()
        if not rows:
            print(f"{SKIP} 找不到热库 >= 5 条公告的 stock_code")
            return None

        stock_code, hot_count = rows
        print(f"  stock_code={stock_code}, 热库公告数={hot_count}")

        repo = AnnouncementRepository(db)

        original_scalars_all = BaseRepository.scalars_all
        cold_called = {"value": False}

        def patched_scalars_all(self, stmt):
            stmt_str = str(stmt)
            if "announcement_archive" in stmt_str.lower():
                cold_called["value"] = True
            return original_scalars_all(self, stmt)

        with patch.object(BaseRepository, "scalars_all", patched_scalars_all):
            results = repo.list_raw_announcements(stock_code, days=3650)

        print(f"  查询返回 {len(results)} 条")
        print(f"  冷库被查询: {cold_called['value']}")

        if len(results) >= 5 and not cold_called["value"]:
            print(f"{PASS} 热库 >= 5 条时未查冷库（边界正确）")
            return True
        elif cold_called["value"]:
            print(f"{FAIL} 热库 >= 5 条但仍查了冷库")
            return False
        else:
            print(f"{SKIP} 结果不足 5 条")
            return None
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 4: News 单条查询冷库回退
# ─────────────────────────────────────────────
def test_single_record_cold_fallback():
    print()
    print(SEP)
    print("Test 4: 单条查询（get_by_id）冷库回退")
    print(SEP)

    db = SessionLocal()
    try:
        # 找一条只在冷库存在的记录
        cold_row = db.execute(select(NewsArchive).limit(1)).scalars().first()
        if not cold_row:
            # 尝试 financial
            cold_row = db.execute(select(FinancialArchive).limit(1)).scalars().first()
            if not cold_row:
                print(f"{SKIP} 所有冷库表为空")
                return None

            cold_id = cold_row.id
            hot_exists = db.execute(
                select(FinancialHot).where(FinancialHot.id == cold_id)
            ).scalars().first()

            if hot_exists:
                print(f"{SKIP} 冷库记录 id={cold_id} 在热库也存在（id 冲突）")
                return None

            repo = FinancialRepository(db)
            result = repo.get_financial_note_by_id(cold_id)
            print(f"  查询 financial_archive id={cold_id}")
            print(f"  结果: {'找到' if result else '未找到'}")

            if result:
                print(f"{PASS} 单条查询冷库回退成功")
                return True
            else:
                print(f"{FAIL} 冷库记录未被查到")
                return False

        cold_id = cold_row.id
        hot_exists = db.execute(
            select(NewsHot).where(NewsHot.id == cold_id)
        ).scalars().first()

        if hot_exists:
            print(f"{SKIP} 冷库记录 id={cold_id} 在热库也存在")
            return None

        repo = NewsRepository(db)
        result = repo.get_news_raw_by_id(cold_id)
        print(f"  查询 news_archive id={cold_id}")
        print(f"  结果: {'找到' if result else '未找到'}")

        if result:
            print(f"{PASS} 单条查询冷库回退成功")
            return True
        else:
            print(f"{FAIL} 冷库记录未被查到")
            return False
    finally:
        db.close()


# ─────────────────────────────────────────────
# Test 5: 各表冷库数据统计
# ─────────────────────────────────────────────
def test_cold_data_stats():
    print()
    print(SEP)
    print("Test 5: 各表冷库数据统计")
    print(SEP)

    db = SessionLocal()
    try:
        tables = [
            ("news_archive", NewsArchive),
            ("announcement_archive", AnnouncementArchive),
            ("financial_archive", FinancialArchive),
            ("research_report_archive", ResearchReportArchive),
        ]
        for name, model in tables:
            count = db.execute(select(func.count(model.id))).scalar() or 0
            print(f"  {name}: {count} 条")

        hot_tables = [
            ("news_hot", NewsHot),
            ("announcement_hot", AnnouncementHot),
            ("financial_hot", FinancialHot),
            ("research_report_hot", ResearchReportHot),
        ]
        for name, model in hot_tables:
            count = db.execute(select(func.count(model.id))).scalar() or 0
            print(f"  {name}: {count} 条")

        print(f"{PASS} 统计完成")
        return True
    finally:
        db.close()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n[冷库回退阈值测试 COLD_FALLBACK_THRESHOLD=5]\n")

    tests = [
        ("阈值常量验证", test_threshold_value),
        ("热库充足不查冷库", test_hot_sufficient_no_cold),
        ("热库不足查冷库补充", test_hot_insufficient_cold_fallback),
        ("边界值恰好5条", test_boundary_exactly_5),
        ("单条查询冷库回退", test_single_record_cold_fallback),
        ("冷热库数据统计", test_cold_data_stats),
    ]

    results = []
    for name, fn in tests:
        try:
            result = fn()
            results.append((name, result))
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
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
