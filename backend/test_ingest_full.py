"""全量入库流程测试（直接调用 service 层 + ORM）。"""

import json
import sys
import traceback
from datetime import datetime

sys.path.insert(0, ".")

from app.core.database.session import SessionLocal
from app.core.database.models.company import Company, IndustryMaster
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.news_hot import NewsHot
from app.core.database.models.macro_hot import MacroIndicator
from sqlalchemy import select, text, delete

PASS = 0
FAIL = 0
ERRORS = []


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def expect(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        log(f"  PASS  {name}")
    else:
        FAIL += 1
        ERRORS.append(f"{name}: {detail}")
        log(f"  FAIL  {name}  — {detail}")


def count_table(table_name):
    db = SessionLocal()
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
log("=" * 60)
log("入库全量测试开始（直接 ORM）")
log("=" * 60)

before = {}
for t in ["company", "financial_hot", "announcement_hot", "news_hot", "macro_indicator", "research_report_hot"]:
    before[t] = count_table(t)
    log(f"  测试前 {t}: {before[t]}")

# ═══════════════════════════════════════════════════════
# 1. 公司
# ═══════════════════════════════════════════════════════
log("\n─── 1. 公司 ───")
db = SessionLocal()
try:
    # 新增
    c1 = Company(stock_code="999901", stock_name="测试药业", exchange="SZ",
                 industry_level1="医药生物", industry_level2="创新药",
                 business_summary="测试公司主营创新药")
    c2 = Company(stock_code="999902", stock_name="测试医疗", exchange="SH",
                 business_summary="第二家测试公司")
    db.add(c1)
    db.add(c2)
    db.commit()
    expect("新增公司 999901+999902", count_table("company") == before["company"] + 2)

    # 更新
    c1 = db.execute(select(Company).where(Company.stock_code == "999901")).scalars().first()
    c1.business_summary = "测试公司（已更新）"
    db.commit()
    c1 = db.execute(select(Company).where(Company.stock_code == "999901")).scalars().first()
    expect("更新公司 999901", c1.business_summary == "测试公司（已更新）", c1.business_summary)

    # 重复插入（应报错或跳过）
    try:
        dup = Company(stock_code="999901", stock_name="重复")
        db.add(dup)
        db.flush()
        db.rollback()
        expect("重复公司应冲突", False, "未报错")
    except Exception:
        db.rollback()
        expect("重复公司应冲突", True)
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 2. 财务
# ═══════════════════════════════════════════════════════
log("\n─── 2. 财务 ───")
db = SessionLocal()
try:
    f1 = FinancialHot(
        stock_code="999901", report_date="2024-12-31", report_type="annual",
        fiscal_year=2024, revenue=5000000000, operating_cost=2000000000,
        gross_profit=3000000000, gross_margin=0.6,
        net_profit=1200000000, eps=2.50,
        total_assets=10000000000, total_liabilities=3000000000, debt_ratio=0.3,
        rd_expense=800000000, rd_ratio=0.16,
        operating_cashflow=1400000000,
    )
    db.add(f1)
    db.flush()
    expect("新增财务-年报 999901", True)

    f2 = FinancialHot(
        stock_code="999901", report_date="2024-06-30", report_type="semiannual",
        fiscal_year=2024, revenue=2200000000, net_profit=500000000, eps=1.10,
    )
    db.add(f2)
    db.flush()
    expect("新增财务-半年报 999901", True)

    f3 = FinancialHot(
        stock_code="999902", report_date="2024-12-31", report_type="annual",
        fiscal_year=2024, revenue=3000000000, net_profit=800000000, eps=1.80,
    )
    db.add(f3)
    db.flush()
    expect("新增财务-年报 999902", True)

    # upsert: 更新已有记录
    existing = db.execute(select(FinancialHot).where(
        FinancialHot.stock_code == "999901",
        FinancialHot.report_date == "2024-12-31",
        FinancialHot.report_type == "annual",
    )).scalars().first()
    existing.revenue = 5100000000
    existing.eps = 2.55
    db.flush()
    expect("更新财务(upsert) 999901", existing.eps == 2.55)

    db.commit()
    after = count_table("financial_hot")
    expect(f"financial_hot +3", after == before["financial_hot"] + 3, f"got {after - before['financial_hot']}")
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 3. 公告
# ═══════════════════════════════════════════════════════
log("\n─── 3. 公告 ───")
db = SessionLocal()
try:
    import hashlib
    def md5(s): return hashlib.md5(s.encode()).hexdigest()

    a1 = AnnouncementHot(
        announcement_uid=md5("999901-药品获批公告-2024-11-15"),
        stock_code="999901", title="关于测试药品A获得上市批准的公告",
        publish_date="2024-11-15", announcement_type="drug_approval",
        content="本公司药品测试药品A获得国家药监局批准上市。",
    )
    db.add(a1)
    db.flush()
    expect("新增公告-药品获批", True)

    a2 = AnnouncementHot(
        announcement_uid=md5("999901-年报摘要-2025-03-28"),
        stock_code="999901", title="2024年年度报告摘要",
        publish_date="2025-03-28", announcement_type="financial_report",
        content="本公司发布2024年年度报告。",
    )
    db.add(a2)
    db.flush()
    expect("新增公告-年报摘要", True)

    a3 = AnnouncementHot(
        announcement_uid=md5("999902-战略合作-2024-12-01"),
        stock_code="999902", title="关于签署战略合作协议的公告",
        publish_date="2024-12-01", announcement_type="general",
    )
    db.add(a3)
    db.flush()
    expect("新增公告-战略合作 999902", True)

    # upsert
    existing = db.execute(select(AnnouncementHot).where(
        AnnouncementHot.announcement_uid == md5("999901-药品获批公告-2024-11-15")
    )).scalars().first()
    existing.content = "更新后的公告内容"
    db.flush()
    expect("更新公告(upsert)", existing.content == "更新后的公告内容")

    db.commit()
    after = count_table("announcement_hot")
    expect(f"announcement_hot +3", after == before["announcement_hot"] + 3, f"got {after - before['announcement_hot']}")
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 4. 研报
# ═══════════════════════════════════════════════════════
log("\n─── 4. 研报 ───")
db = SessionLocal()
try:
    r1 = ResearchReportHot(
        report_uid=md5("company-999901-测试药业深度研究报告"),
        scope_type="company", stock_code="999901",
        title="测试药业深度研究报告", publish_date="2024-10-15",
        report_org="测试证券", content="深度研究报告正文……",
        summary_text="看好公司创新药管线。",
    )
    db.add(r1)
    db.flush()
    expect("新增研报-公司研报 999901", True)

    # 行业研报（industry_code 不存在时设为 None）
    r2 = ResearchReportHot(
        report_uid=md5("industry-创新药行业2024年度报告"),
        scope_type="industry", stock_code=None, industry_code=None,
        title="创新药行业2024年度报告", publish_date="2025-01-10",
        report_org="测试研究所", content="行业报告正文……",
    )
    db.add(r2)
    db.flush()
    expect("新增研报-行业研报(无外键)", True)

    r3 = ResearchReportHot(
        report_uid=md5("company-999902-测试医疗投资价值分析"),
        scope_type="company", stock_code="999902",
        title="测试医疗投资价值分析", publish_date="2024-12-20",
        report_org="另一家券商",
    )
    db.add(r3)
    db.flush()
    expect("新增研报-公司研报 999902", True)

    db.commit()
    after = count_table("research_report_hot")
    expect(f"research_report_hot +3", after == before["research_report_hot"] + 3, f"got {after - before['research_report_hot']}")
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 5. 新闻
# ═══════════════════════════════════════════════════════
log("\n─── 5. 新闻 ───")
db = SessionLocal()
try:
    n1 = NewsHot(
        news_uid="test_news_001", title="医保政策调整影响创新药行业",
        publish_time="2024-12-05 10:30:00", source_name="测试财经网",
        news_type="policy_news", content="医保政策调整对创新药行业影响分析……",
        related_stock_codes_json=["999901"],
    )
    db.add(n1)
    db.flush()
    expect("新增新闻-政策新闻", True)

    n2 = NewsHot(
        news_uid="test_news_002", title="测试药业新药临床三期数据积极",
        publish_time="2024-11-20 14:00:00", source_name="测试财经网",
        news_type="company_news", content="测试药业发布新药临床三期数据……",
        related_stock_codes_json=["999901"],
    )
    db.add(n2)
    db.flush()
    expect("新增新闻-公司新闻", True)

    # upsert
    existing = db.execute(select(NewsHot).where(NewsHot.news_uid == "test_news_001")).scalars().first()
    existing.content = "更新后的新闻内容"
    db.flush()
    expect("更新新闻(upsert)", existing.content == "更新后的新闻内容")

    db.commit()
    after = count_table("news_hot")
    expect(f"news_hot +2", after == before["news_hot"] + 2, f"got {after - before['news_hot']}")
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 6. 宏观指标
# ═══════════════════════════════════════════════════════
log("\n─── 6. 宏观指标 ───")
db = SessionLocal()
try:
    m1 = MacroIndicator(
        indicator_name="测试PMI指标", period="2024-12",
        value=51.8, unit="%", category="行业景气度",
    )
    db.add(m1)
    db.flush()
    expect("新增宏观-PMI", True)

    m2 = MacroIndicator(
        indicator_name="测试固投增速", period="2024-Q4",
        value=8.5, unit="%", category="投资",
    )
    db.add(m2)
    db.flush()
    expect("新增宏观-固投", True)

    # upsert
    existing = db.execute(select(MacroIndicator).where(
        MacroIndicator.indicator_name == "测试PMI指标",
        MacroIndicator.period == "2024-12",
    )).scalars().first()
    existing.value = 52.0
    db.flush()
    expect("更新宏观(upsert)", float(existing.value) == 52.0)

    db.commit()
    after = count_table("macro_indicator")
    expect(f"macro_indicator +2", after == before["macro_indicator"] + 2, f"got {after - before['macro_indicator']}")
finally:
    db.close()

# ═══════════════════════════════════════════════════════
# 7. 验证前端 API 读取
# ═══════════════════════════════════════════════════════
log("\n─── 7. 验证前端 API 读取 ───")
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

r = client.get("/api/stock/companies")
expect("GET /api/stock/companies 200", r.status_code == 200, f"HTTP {r.status_code}")
companies = r.json()
test_found = [c for c in companies if c["symbol"] in ("999901", "999902")]
expect("公司列表包含测试公司", len(test_found) == 2, f"found {len(test_found)}")

r = client.get("/api/stock/company", params={"symbol": "999901", "compact": "true"})
expect("GET /api/stock/company 200", r.status_code == 200, f"HTTP {r.status_code}")
dataset = r.json()
for key, min_count in [("financial_abstract", 1), ("announcements", 1), ("research_reports", 1), ("news", 1)]:
    items = dataset.get(key, [])
    expect(f"999901.{key} >= {min_count}", len(items) >= min_count, f"got {len(items)}")

# ═══════════════════════════════════════════════════════
# 8. 验证 import_batch.py 语法和导入
# ═══════════════════════════════════════════════════════
log("\n─── 8. 验证 import_batch.py ───")
try:
    import import_batch
    expect("import_batch.py 导入成功", True)
    expect("import_batch 有 process_batch", hasattr(import_batch, "process_batch"))
    expect("import_batch 有 6 个 handler", len(import_batch.HANDLERS) == 6, f"got {len(import_batch.HANDLERS)}")
except Exception as e:
    expect("import_batch.py 导入成功", False, str(e))

# ═══════════════════════════════════════════════════════
# 9. 清理
# ═══════════════════════════════════════════════════════
log("\n─── 9. 清理测试数据 ───")
db = SessionLocal()
try:
    db.execute(delete(ResearchReportHot).where(ResearchReportHot.stock_code.in_(["999901", "999902"])))
    db.execute(text("DELETE FROM research_report_hot WHERE report_uid LIKE '%创新药行业%'"))
    db.execute(delete(FinancialHot).where(FinancialHot.stock_code.in_(["999901", "999902"])))
    db.execute(delete(AnnouncementHot).where(AnnouncementHot.stock_code.in_(["999901", "999902"])))
    db.execute(delete(NewsHot).where(NewsHot.news_uid.in_(["test_news_001", "test_news_002"])))
    db.execute(text("DELETE FROM macro_indicator WHERE indicator_name LIKE '测试%'"))
    db.execute(text("DELETE FROM watchlist WHERE stock_code IN ('999901','999902')"))
    db.execute(delete(Company).where(Company.stock_code.in_(["999901", "999902"])))
    db.commit()
    log("  测试数据已清理")
except Exception as e:
    db.rollback()
    log(f"  清理失败: {e}")
finally:
    db.close()

for t in ["company", "financial_hot", "announcement_hot", "news_hot", "macro_indicator", "research_report_hot"]:
    after = count_table(t)
    status = "OK" if after == before[t] else f"MISMATCH (before={before[t]})"
    log(f"  {t}: {after} {status}")

# ═══════════════════════════════════════════════════════
log("\n" + "=" * 60)
log(f"测试完成: {PASS} 通过, {FAIL} 失败")
if ERRORS:
    log("失败详情:")
    for e in ERRORS:
        log(f"  - {e}")
log("=" * 60)
sys.exit(1 if FAIL > 0 else 0)
