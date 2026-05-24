"""
种子数据脚本 — 向数据库写入测试用假数据。
运行方式：在 backend 目录下执行
    python ../seed_data.py
或在项目根目录执行
    python seed_data.py
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta
import random
import uuid

# Windows 终端强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 把 backend 加入 sys.path，以便复用项目的 config / models
BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

os.chdir(BACKEND)  # config.py 用相对路径找 .env，需要切到 backend 目录

from sqlalchemy.orm import Session
from app.core.database.session import SessionLocal, engine
from app.core.database.base import Base
from app.core.database.models.company import Company, IndustryMaster
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.news_hot import NewsHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.macro_hot import MacroIndicator
from app.core.database.models.user import User
import hashlib

# ── 建表（如果还没建） ────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── 假数据定义 ────────────────────────────────────────────────────────────────

INDUSTRIES = [
    ("pharma_chem",    "化学制药",   "pharma",    "医药生物"),
    ("pharma_bio",     "生物制品",   "pharma",    "医药生物"),
    ("pharma_tcm",     "中药",       "pharma",    "医药生物"),
    ("pharma_device",  "医疗器械",   "pharma",    "医药生物"),
    ("pharma_service", "医疗服务",   "pharma",    "医药生物"),
]

COMPANIES = [
    # (stock_code, stock_name, full_name, exchange, industry_code, industry_level2, listing_date)
    ("600276", "恒瑞医药", "江苏恒瑞医药股份有限公司", "SSE", "pharma_chem", "化学制药", date(2000, 10, 18)),
    ("000858", "五粮液",   "宜宾五粮液股份有限公司",   "SZSE","pharma_chem", "化学制药", date(1998, 4, 27)),
    ("300760", "迈瑞医疗", "迈瑞医疗国际股份有限公司", "SZSE","pharma_device","医疗器械",date(2018, 10, 16)),
    ("002007", "华兰生物", "华兰生物工程股份有限公司", "SZSE","pharma_bio",  "生物制品", date(2004, 7, 30)),
    ("600196", "复星医药", "上海复星医药（集团）股份有限公司","SSE","pharma_chem","化学制药",date(1998, 8, 7)),
    ("300347", "泰格医药", "泰格医药科技股份有限公司", "SZSE","pharma_service","医疗服务",date(2012, 8, 23)),
    ("600085", "同仁堂",   "中国北京同仁堂（集团）股份有限公司","SSE","pharma_tcm","中药",date(1997, 6, 25)),
    ("002252", "上海莱士", "上海莱士血液制品股份有限公司","SZSE","pharma_bio","生物制品",date(2008, 6, 27)),
]

REPORT_ORGS = ["中信证券", "国泰君安", "华泰证券", "招商证券", "海通证券", "广发证券", "兴业证券", "申万宏源"]

ANNOUNCEMENT_TYPES = ["定期报告", "重大事项", "股权变动", "业绩预告", "新药申报", "临床试验", "集采中标", "监管函"]

NEWS_TYPES = ["行业动态", "政策解读", "公司新闻", "市场分析", "研发进展", "集采动态"]

PIPELINE_DRUGS = {
    "600276": [
        ("SHR-1210（卡瑞利珠单抗）", "PD-1抑制剂", "已上市", "肺癌/肝癌/食管癌"),
        ("SHR-1701", "PD-L1/TGF-β双抗", "III期临床", "非小细胞肺癌"),
        ("SHR-A1811", "HER2 ADC", "II期临床", "乳腺癌"),
        ("SHR-2554", "EZH2抑制剂", "I期临床", "淋巴瘤"),
    ],
    "300760": [
        ("迈瑞监护仪N系列", "患者监护", "已上市", "ICU/手术室"),
        ("迈瑞超声DC-80", "彩色超声", "已上市", "心脏/腹部"),
        ("迈瑞血液分析仪BC-7500", "体外诊断", "已上市", "血常规"),
    ],
    "002007": [
        ("静注人免疫球蛋白", "血液制品", "已上市", "免疫缺陷"),
        ("人凝血因子VIII", "血液制品", "已上市", "血友病A"),
        ("四价流感病毒裂解疫苗", "疫苗", "已上市", "流感预防"),
    ],
    "600196": [
        ("汉利康（利妥昔单抗）", "生物类似药", "已上市", "淋巴瘤"),
        ("苏可欣（马来酸阿伐曲泊帕）", "化学药", "已上市", "血小板减少症"),
        ("复必泰（mRNA新冠疫苗）", "疫苗", "已上市", "新冠预防"),
    ],
}


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def uid() -> str:
    return uuid.uuid4().hex


def make_financial(stock_code: str, year: int, report_type: str, base_rev: float) -> FinancialHot:
    """生成一条财务记录，数值有一定随机波动。"""
    rev = base_rev * random.uniform(0.92, 1.12)
    cost_ratio = random.uniform(0.38, 0.55)
    cost = rev * cost_ratio
    gross = rev - cost
    gross_margin = gross / rev
    selling = rev * random.uniform(0.08, 0.14)
    admin = rev * random.uniform(0.04, 0.08)
    rd = rev * random.uniform(0.10, 0.18)
    op_profit = gross - selling - admin - rd
    net = op_profit * random.uniform(0.78, 0.88)
    net_deducted = net * random.uniform(0.92, 1.0)
    total_assets = rev * random.uniform(1.8, 2.8)
    total_liab = total_assets * random.uniform(0.25, 0.45)
    op_cf = net * random.uniform(0.9, 1.3)

    quarter_map = {"年报": f"{year}-12-31", "三季报": f"{year}-09-30",
                   "中报": f"{year}-06-30", "一季报": f"{year}-03-31"}
    report_date = date.fromisoformat(quarter_map[report_type])

    return FinancialHot(
        stock_code=stock_code,
        report_date=report_date,
        fiscal_year=year,
        report_type=report_type,
        revenue=round(rev, 2),
        operating_cost=round(cost, 2),
        gross_profit=round(gross, 2),
        gross_margin=round(gross_margin, 6),
        selling_expense=round(selling, 2),
        admin_expense=round(admin, 2),
        rd_expense=round(rd, 2),
        rd_ratio=round(rd / rev, 6),
        operating_profit=round(op_profit, 2),
        net_profit=round(net, 2),
        net_profit_deducted=round(net_deducted, 2),
        eps=round(net / 1e9 * random.uniform(0.8, 1.2), 4),
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liab, 2),
        debt_ratio=round(total_liab / total_assets, 6),
        operating_cashflow=round(op_cf, 2),
        investing_cashflow=round(-rev * random.uniform(0.05, 0.15), 2),
        financing_cashflow=round(rev * random.uniform(-0.08, 0.05), 2),
        query_count=random.randint(0, 200),
    )


def make_announcement(stock_code: str, stock_name: str, ann_type: str, pub_date: date) -> AnnouncementHot:
    templates = {
        "定期报告": (
            f"{stock_name}{pub_date.year}年{'年度' if pub_date.month==3 else '半年度'}报告",
            f"{stock_name}发布{pub_date.year}年度报告，报告期内公司实现营业收入同比增长，净利润稳步提升，研发投入持续加大。"
        ),
        "新药申报": (
            f"{stock_name}关于新药上市申请获受理的公告",
            f"{stock_name}收到国家药品监督管理局出具的《受理通知书》，公司申报的创新药已获受理，进入审评程序。"
        ),
        "临床试验": (
            f"{stock_name}关于创新药物临床试验进展的公告",
            f"{stock_name}在研创新药物III期临床试验达到主要终点，数据显示与对照组相比具有统计学显著差异，安全性良好。"
        ),
        "集采中标": (
            f"{stock_name}关于参与国家集中采购中标结果的公告",
            f"{stock_name}参与第X批国家组织药品集中采购，公司产品成功中标，中标价格较市场价降幅约30%，预计影响当年收入约X亿元。"
        ),
        "业绩预告": (
            f"{stock_name}{pub_date.year}年{'上半年' if pub_date.month<=6 else '全年'}业绩预告",
            f"{stock_name}预计{pub_date.year}年净利润同比增长15%-25%，主要原因为核心产品销售放量及新产品上市贡献增量收入。"
        ),
        "重大事项": (
            f"{stock_name}关于签署战略合作协议的公告",
            f"{stock_name}与国际知名医药企业签署战略合作协议，双方将在创新药研发、商业化推广等领域开展深度合作。"
        ),
        "股权变动": (
            f"{stock_name}关于股东增持股份的公告",
            f"{stock_name}控股股东计划在未来6个月内增持公司股份不低于1亿元，彰显对公司长期发展的信心。"
        ),
        "监管函": (
            f"{stock_name}关于收到监管关注函的公告及回复",
            f"{stock_name}收到交易所监管关注函，就公司近期信息披露事项进行说明，公司已按要求进行详细回复。"
        ),
    }
    title, summary = templates.get(ann_type, (f"{stock_name}公告", "公司发布相关公告。"))
    return AnnouncementHot(
        announcement_uid=uid(),
        stock_code=stock_code,
        title=title,
        publish_date=pub_date,
        announcement_type=ann_type,
        summary_text=summary,
        content=summary + "（详见附件全文）",
        vector_status="pending",
        query_count=random.randint(0, 100),
    )


def make_news(stock_code: str, stock_name: str, news_type: str, pub_time: datetime) -> NewsHot:
    templates = {
        "行业动态": f"医药行业政策持续利好，{stock_name}等龙头企业有望受益于集采扩围和医保谈判新规。",
        "政策解读": f"国家医保局发布新版医保目录，{stock_name}多款产品纳入，预计带动销量显著提升。",
        "公司新闻": f"{stock_name}发布最新研发进展，核心管线产品临床数据亮眼，市场预期持续升温。",
        "市场分析": f"分析师上调{stock_name}目标价，认为公司研发管线丰富、商业化能力强，维持买入评级。",
        "研发进展": f"{stock_name}创新药物获得FDA快速通道资格认定，国际化进程加速推进。",
        "集采动态": f"第X批国家集采结果出炉，{stock_name}产品中标，市场份额有望进一步扩大。",
    }
    content = templates.get(news_type, f"{stock_name}相关新闻报道。")
    return NewsHot(
        news_uid=uid(),
        title=content[:50],
        publish_time=pub_time,
        source_name=random.choice(["财联社", "21世纪经济报道", "证券时报", "上海证券报", "医药经济报"]),
        news_type=news_type,
        content=content,
        summary_text=content,
        related_stock_codes_json=[stock_code],
        vector_status="pending",
        query_count=random.randint(0, 80),
    )


def make_report(stock_code: str, stock_name: str, pub_date: date, org: str) -> ResearchReportHot:
    ratings = ["买入", "增持", "中性"]
    rating = random.choice(ratings)
    target = round(random.uniform(30, 200), 1)
    summary = (
        f"【{org}】{stock_name}深度研究报告\n"
        f"评级：{rating} | 目标价：{target}元\n\n"
        f"核心观点：{stock_name}作为医药行业龙头，研发管线丰富，商业化能力突出。"
        f"预计{pub_date.year+1}年营收同比增长18%-22%，净利润增速有望超预期。"
        f"公司持续加大研发投入，创新药占比逐年提升，长期成长逻辑清晰。\n\n"
        f"风险提示：集采降价超预期、研发管线失败、市场竞争加剧。"
    )
    return ResearchReportHot(
        report_uid=uid(),
        scope_type="company",
        stock_code=stock_code,
        title=f"{stock_name}深度研究：{rating}评级，目标价{target}元",
        publish_date=pub_date,
        report_org=org,
        summary_text=summary,
        content=summary,
        source_type="research_report",
        vector_status="pending",
        query_count=random.randint(0, 150),
    )


def make_macro(name: str, period: str, period_date: date, value: float, unit: str, category: str) -> MacroIndicator:
    return MacroIndicator(
        indicator_name=name,
        period=period,
        period_date=period_date,
        value=round(value, 6),
        unit=unit,
        category=category,
        summary_text=f"{name} {period} 数据为 {value:.2f}{unit}。",
        source_type="wind",
    )


# ── 主逻辑 ────────────────────────────────────────────────────────────────────

def seed(db: Session) -> None:
    print("开始写入种子数据...")

    # 1. 确保 demo 用户存在
    if not db.query(User).filter_by(id=1).first():
        db.add(User(
            id=1,
            username="demo_user",
            password_hash=hashlib.sha256(b"demo1234").hexdigest(),
            role="user",
            status="active",
        ))
        db.flush()
        print("  ✓ 创建 demo_user")

    # 2. 行业
    existing_industries = {r.industry_code for r in db.query(IndustryMaster.industry_code).all()}
    for code, name, parent, _ in INDUSTRIES:
        if code not in existing_industries:
            db.add(IndustryMaster(industry_code=code, industry_name=name, parent_industry_code=parent))
    db.flush()
    print(f"  ✓ 行业数据（{len(INDUSTRIES)} 条）")

    # 3. 公司
    existing_companies = {r.stock_code for r in db.query(Company.stock_code).all()}
    new_companies = []
    for sc, sn, fn, ex, ic, il2, ld in COMPANIES:
        if sc not in existing_companies:
            c = Company(
                stock_code=sc, stock_name=sn, full_name=fn,
                exchange=ex, industry_level1="医药生物",
                industry_code=ic, industry_level2=il2,
                listing_date=ld,
                business_summary=f"{sn}是中国领先的医药企业，专注于{il2}领域，拥有完整的研发、生产和销售体系。",
                core_products_json=PIPELINE_DRUGS.get(sc, []),
            )
            db.add(c)
            new_companies.append(sc)
    db.flush()
    print(f"  ✓ 公司数据（新增 {len(new_companies)} 家）")

    # 4. 财务数据 — 每家公司近 4 年 × 4 个报告期
    base_revenues = {
        "600276": 25e9, "000858": 66e9, "300760": 30e9, "002007": 6e9,
        "600196": 43e9, "300347": 7e9,  "600085": 16e9, "002252": 10e9,
    }
    fin_count = 0
    for sc, *_ in COMPANIES:
        base = base_revenues.get(sc, 10e9)
        for year in range(2021, 2025):
            growth = 1 + (year - 2021) * random.uniform(0.05, 0.15)
            for rtype in ["年报", "中报", "一季报", "三季报"]:
                ratio = {"年报": 1.0, "中报": 0.48, "一季报": 0.22, "三季报": 0.75}[rtype]
                exists = db.query(FinancialHot).filter_by(
                    stock_code=sc,
                    fiscal_year=year,
                    report_type=rtype,
                ).first()
                if not exists:
                    db.add(make_financial(sc, year, rtype, base * growth * ratio))
                    fin_count += 1
    db.flush()
    print(f"  ✓ 财务数据（新增 {fin_count} 条）")

    # 5. 公告 — 每家公司近 2 年，每种类型各 1-2 条
    ann_count = 0
    for sc, sn, *_ in COMPANIES:
        for ann_type in ANNOUNCEMENT_TYPES:
            for _ in range(random.randint(1, 2)):
                pub = rand_date(date(2023, 1, 1), date(2025, 5, 1))
                exists = db.query(AnnouncementHot).filter_by(
                    stock_code=sc, announcement_type=ann_type, publish_date=pub
                ).first()
                if not exists:
                    db.add(make_announcement(sc, sn, ann_type, pub))
                    ann_count += 1
    db.flush()
    print(f"  ✓ 公告数据（新增 {ann_count} 条）")

    # 6. 新闻 — 每家公司近 1 年，每种类型各 2 条
    news_count = 0
    for sc, sn, *_ in COMPANIES:
        for ntype in NEWS_TYPES:
            for _ in range(2):
                pub = datetime.combine(
                    rand_date(date(2024, 1, 1), date(2025, 5, 20)),
                    datetime.min.time()
                ).replace(hour=random.randint(8, 20), minute=random.randint(0, 59))
                db.add(make_news(sc, sn, ntype, pub))
                news_count += 1
    db.flush()
    print(f"  ✓ 新闻数据（新增 {news_count} 条）")

    # 7. 研报 — 每家公司近 2 年，每家券商各 1 份
    rr_count = 0
    for sc, sn, *_ in COMPANIES:
        for org in random.sample(REPORT_ORGS, 4):
            pub = rand_date(date(2023, 6, 1), date(2025, 5, 1))
            exists = db.query(ResearchReportHot).filter_by(
                stock_code=sc, report_org=org, publish_date=pub
            ).first()
            if not exists:
                db.add(make_report(sc, sn, pub, org))
                rr_count += 1
    db.flush()
    print(f"  ✓ 研报数据（新增 {rr_count} 条）")

    # 8. 宏观指标
    macro_defs = [
        ("CPI同比", "%", "通胀"),
        ("PPI同比", "%", "通胀"),
        ("GDP增速", "%", "经济增长"),
        ("社会消费品零售总额增速", "%", "消费"),
        ("医药制造业工业增加值增速", "%", "医药行业"),
        ("医保基金收入增速", "%", "医保"),
        ("新药批准数量", "个", "医药监管"),
        ("集采降价幅度", "%", "集采"),
    ]
    macro_count = 0
    base_values = {
        "CPI同比": 2.1, "PPI同比": -1.5, "GDP增速": 5.2,
        "社会消费品零售总额增速": 7.2, "医药制造业工业增加值增速": 6.8,
        "医保基金收入增速": 9.5, "新药批准数量": 48, "集采降价幅度": 52.0,
    }
    for year in range(2022, 2026):
        for q in range(1, 5):
            if year == 2025 and q > 1:
                continue
            period = f"{year}Q{q}"
            period_date = date(year, q * 3, 28 if q in (1, 4) else 30)
            for name, unit, category in macro_defs:
                exists = db.query(MacroIndicator).filter_by(
                    indicator_name=name, period=period
                ).first()
                if not exists:
                    base = base_values[name]
                    val = base * random.uniform(0.85, 1.15)
                    db.add(make_macro(name, period, period_date, val, unit, category))
                    macro_count += 1
    db.flush()
    print(f"  ✓ 宏观指标（新增 {macro_count} 条）")

    db.commit()
    print("\n全部种子数据写入完成！")
    print(f"  公司：{len(COMPANIES)} 家")
    print(f"  财务：{fin_count} 条")
    print(f"  公告：{ann_count} 条")
    print(f"  新闻：{news_count} 条")
    print(f"  研报：{rr_count} 条")
    print(f"  宏观：{macro_count} 条")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    except Exception as e:
        db.rollback()
        print(f"\n❌ 写入失败：{e}")
        raise
    finally:
        db.close()
