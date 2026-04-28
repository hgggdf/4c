"""
插入两家对比鲜明的测试公司 testa / testb，覆盖行业对比分析的完整流程。

testa: 高毛利率、高ROE、低负债、强研发 → 优秀
testb: 低毛利率、低ROE、高负债、弱研发 → 较差

运行方式：
    cd backend
    python seed_test_companies.py

清除方式：
    python seed_test_companies.py --clean
"""

import sys
from datetime import date, datetime

sys.path.insert(0, ".")

from app.core.database.session import SessionLocal
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.news_hot import NewsHot

# ── 公司定义 ──────────────────────────────────────────────────────────────────

COMPANIES = [
    {
        "stock_code": "testa",
        "stock_name": "测试优质药业",
        "full_name": "测试优质药业股份有限公司",
        "exchange": "SH",
        "industry_level1": "医药生物",
        "industry_level2": "创新药",
        "business_summary": "专注于创新药研发，核心产品覆盖肿瘤、自免领域，研发管线丰富，毛利率行业领先。",
    },
    {
        "stock_code": "testb",
        "stock_name": "测试普通仿制药",
        "full_name": "测试普通仿制药股份有限公司",
        "exchange": "SZ",
        "industry_level1": "医药生物",
        "industry_level2": "仿制药",
        "business_summary": "以仿制药为主，产品同质化竞争激烈，受集采政策影响较大，盈利能力承压。",
    },
]

# ── 财务数据（3年，制造对比差异）────────────────────────────────────────────

def _fin(stock_code, year, **kw):
    return dict(stock_code=stock_code, fiscal_year=year,
                report_date=date(year, 12, 31), report_type="年报", **kw)

FINANCIALS = [
    # ── testa: 高毛利、高ROE、低负债、强研发 ──────────────────────────────
    _fin("testa", 2022,
         revenue=8_500_000_000,
         operating_cost=1_190_000_000,
         gross_profit=7_310_000_000,
         gross_margin=86.0,          # 86%
         rd_expense=1_275_000_000,
         rd_ratio=15.0,
         net_profit=2_550_000_000,
         eps=2.55,
         total_assets=18_000_000_000,
         total_liabilities=3_240_000_000,
         debt_ratio=18.0,
         operating_cashflow=2_800_000_000),

    _fin("testa", 2023,
         revenue=10_200_000_000,
         operating_cost=1_428_000_000,
         gross_profit=8_772_000_000,
         gross_margin=86.0,
         rd_expense=1_632_000_000,
         rd_ratio=16.0,
         net_profit=3_264_000_000,
         eps=3.26,
         total_assets=22_000_000_000,
         total_liabilities=3_740_000_000,
         debt_ratio=17.0,
         operating_cashflow=3_500_000_000),

    _fin("testa", 2024,
         revenue=12_500_000_000,
         operating_cost=1_750_000_000,
         gross_profit=10_750_000_000,
         gross_margin=86.0,
         rd_expense=2_125_000_000,
         rd_ratio=17.0,
         net_profit=4_125_000_000,
         eps=4.13,
         total_assets=27_000_000_000,
         total_liabilities=4_320_000_000,
         debt_ratio=16.0,
         operating_cashflow=4_500_000_000),

    # ── testb: 低毛利、低ROE、高负债、弱研发 ──────────────────────────────
    _fin("testb", 2022,
         revenue=6_000_000_000,
         operating_cost=4_800_000_000,
         gross_profit=1_200_000_000,
         gross_margin=20.0,          # 20%
         rd_expense=120_000_000,
         rd_ratio=2.0,
         net_profit=180_000_000,
         eps=0.18,
         total_assets=9_000_000_000,
         total_liabilities=6_300_000_000,
         debt_ratio=70.0,
         operating_cashflow=250_000_000),

    _fin("testb", 2023,
         revenue=5_400_000_000,       # 营收下滑（集采冲击）
         operating_cost=4_428_000_000,
         gross_profit=972_000_000,
         gross_margin=18.0,
         rd_expense=108_000_000,
         rd_ratio=2.0,
         net_profit=54_000_000,
         eps=0.05,
         total_assets=8_500_000_000,
         total_liabilities=6_375_000_000,
         debt_ratio=75.0,
         operating_cashflow=80_000_000),

    _fin("testb", 2024,
         revenue=5_100_000_000,
         operating_cost=4_233_000_000,
         gross_profit=867_000_000,
         gross_margin=17.0,
         rd_expense=102_000_000,
         rd_ratio=2.0,
         net_profit=-150_000_000,     # 亏损 → 触发红色风险信号
         eps=-0.15,
         total_assets=8_000_000_000,
         total_liabilities=6_400_000_000,
         debt_ratio=80.0,             # 触发高负债红色信号
         operating_cashflow=-50_000_000),
]

# ── 公告（触发风险/机会信号）────────────────────────────────────────────────

ANNOUNCEMENTS = [
    # testa: 利好公告
    dict(
        announcement_uid="testa-ann-001",
        stock_code="testa",
        title="关于创新药XA-101获得FDA突破性疗法认定的公告",
        publish_date=date(2024, 11, 15),
        announcement_type="重大事项",
        summary_text="公司核心产品XA-101获得美国FDA突破性疗法认定，有望加速上市进程，预计2026年提交NDA申请。",
    ),
    dict(
        announcement_uid="testa-ann-002",
        stock_code="testa",
        title="2024年度业绩预增公告",
        publish_date=date(2025, 1, 10),
        announcement_type="业绩预告",
        summary_text="预计2024年净利润同比增长约26%，主要受益于核心产品放量及海外授权收入增加。",
    ),
    # testb: 风险公告
    dict(
        announcement_uid="testb-ann-001",
        stock_code="testb",
        title="关于主要产品纳入第九批国家集中采购的公告",
        publish_date=date(2024, 9, 20),
        announcement_type="重大事项",
        summary_text="公司主要产品阿莫西林胶囊、头孢克肟片纳入第九批集采，中标价格较市场价降幅超60%，预计对公司营收产生重大影响。",
    ),
    dict(
        announcement_uid="testb-ann-002",
        stock_code="testb",
        title="2024年度业绩预亏公告",
        publish_date=date(2025, 1, 15),
        announcement_type="业绩预告",
        summary_text="预计2024年归母净利润亏损约1.5亿元，主要原因为集采降价、原材料成本上涨及研发费用增加。",
    ),
]

# ── 新闻（补充信号）──────────────────────────────────────────────────────────

NEWS = [
    dict(
        news_uid="testa-news-001",
        title="测试优质药业创新药管线再获突破，多款产品进入III期临床",
        publish_time=datetime(2024, 10, 8, 9, 0),
        source_name="医药经济报",
        news_type="行业新闻",
        summary_text="测试优质药业在研管线中已有3款产品进入III期临床试验，研发实力持续获市场认可。",
        related_stock_codes_json=["testa"],
    ),
    dict(
        news_uid="testb-news-001",
        title="仿制药企业面临集采压力，测试普通仿制药盈利能力持续承压",
        publish_time=datetime(2024, 11, 3, 10, 0),
        source_name="证券时报",
        news_type="公司新闻",
        summary_text="受多批次集采政策影响，以仿制药为主的企业盈利空间大幅压缩，测试普通仿制药2024年或面临亏损风险。",
        related_stock_codes_json=["testb"],
    ),
]


def clean(db):
    codes = ["testa", "testb"]
    db.query(AnnouncementHot).filter(AnnouncementHot.stock_code.in_(codes)).delete(synchronize_session=False)
    db.query(FinancialHot).filter(FinancialHot.stock_code.in_(codes)).delete(synchronize_session=False)
    db.query(NewsHot).filter(NewsHot.news_uid.in_([n["news_uid"] for n in NEWS])).delete(synchronize_session=False)
    db.query(Company).filter(Company.stock_code.in_(codes)).delete(synchronize_session=False)
    db.commit()
    print("已清除测试数据。")


def seed(db):
    # 公司
    for c in COMPANIES:
        existing = db.get(Company, c["stock_code"])
        if existing:
            for k, v in c.items():
                setattr(existing, k, v)
        else:
            db.add(Company(**c))
    db.flush()

    # 财务
    for f in FINANCIALS:
        existing = (
            db.query(FinancialHot)
            .filter_by(stock_code=f["stock_code"], report_date=f["report_date"], report_type=f["report_type"])
            .first()
        )
        if existing:
            for k, v in f.items():
                setattr(existing, k, v)
        else:
            db.add(FinancialHot(**f))

    # 公告
    for a in ANNOUNCEMENTS:
        existing = db.query(AnnouncementHot).filter_by(announcement_uid=a["announcement_uid"]).first()
        if not existing:
            db.add(AnnouncementHot(**a))

    # 新闻
    for n in NEWS:
        existing = db.query(NewsHot).filter_by(news_uid=n["news_uid"]).first()
        if not existing:
            db.add(NewsHot(**n))

    db.commit()
    print("测试数据写入完成：")
    print("  testa (测试优质药业) — 高毛利86%、低负债16%、净利润持续增长 → 预期评级：优秀")
    print("  testb (测试普通仿制药) — 低毛利17%、高负债80%、2024年亏损 → 预期评级：较差")
    print()
    print("前端测试方式：")
    print("  风险洞察页：在 symbols 里填 testa,testb")
    print("  企业诊断页：分别选择 testa / testb 查看雷达图")
    print("  分析报告页：分别生成两家公司报告对比")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if "--clean" in sys.argv:
            clean(db)
        else:
            seed(db)
    finally:
        db.close()
