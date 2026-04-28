"""
E2E 现实流程入库测试集生成器
生成 raw / staging / quality_report / manifest，不调用任何接口，不写数据库。
"""

import json
import hashlib
import os
import random
from datetime import datetime, timezone, timedelta

# 固定公司池
COMPANIES = [
    {"code": "600276", "name": "恒瑞医药", "exchange": "SSE",
     "full_name": "江苏恒瑞医药股份有限公司", "industry": "C27"},
    {"code": "300122", "name": "智飞生物", "exchange": "SZSE",
     "full_name": "重庆智飞生物制品股份有限公司", "industry": "C27"},
    {"code": "300760", "name": "迈瑞医疗", "exchange": "SZSE",
     "full_name": "深圳迈瑞生物医疗电子股份有限公司", "industry": "C35"},
    {"code": "603259", "name": "药明康德", "exchange": "SSE",
     "full_name": "无锡药明康德新药开发股份有限公司", "industry": "C27"},
    {"code": "002007", "name": "华兰生物", "exchange": "SZSE",
     "full_name": "华兰生物工程股份有限公司", "industry": "C27"},
    {"code": "600196", "name": "复星医药", "exchange": "SSE",
     "full_name": "上海复星医药（集团）股份有限公司", "industry": "C27"},
    {"code": "688271", "name": "联影医疗", "exchange": "SSE",
     "full_name": "上海联影医疗科技股份有限公司", "industry": "C35"},
    {"code": "300015", "name": "爱尔眼科", "exchange": "SZSE",
     "full_name": "爱尔眼科医院集团股份有限公司", "industry": "Q83"},
    {"code": "688363", "name": "华熙生物", "exchange": "SSE",
     "full_name": "华熙生物科技股份有限公司", "industry": "C27"},
    {"code": "600161", "name": "天坛生物", "exchange": "SSE",
     "full_name": "北京天坛生物制品股份有限公司", "industry": "C27"},
]

STOCK_CODES = [c["code"] for c in COMPANIES]

# Physical paths (relative to backend/)
P_RAW = "crawler/raw/e2e"
P_STAGING = "crawler/staging/e2e"
P_QR = "crawler/staging/quality_reports/e2e"
P_MANIFEST = "ingest_center/manifests_e2e"

# Logical paths (used inside manifest files, prefixed with backend/)
L_RAW = "backend/crawler/raw/e2e"
L_STAGING = "backend/crawler/staging/e2e"
L_QR = "backend/crawler/staging/quality_reports/e2e"

random.seed(42)


def write_json(path: str, data: dict) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def gen_manifest(
    job_id: str,
    category: str,
    endpoint: str,
    ingest_package: str,
    ingest_field: str,
    target_table: str,
    raw_path: str,
    staging_path: str,
    qr_path: str,
    raw_count: int,
    staging_count: int,
    expected_write_count: int,
    sha256: str,
) -> dict:
    return {
        "spec_version": "1.0",
        "staging_format_version": "1.0",
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "producer": {
            "system": "openclaw",
            "module": "E2EGenerator",
            "run_id": f"run_e2e_{job_id}",
        },
        "data_category": category,
        "time_window": {"begin_date": "2026-01-01", "end_date": "2026-03-31"},
        "target": {
            "endpoint": endpoint,
            "ingest_package": ingest_package,
            "ingest_field": ingest_field,
            "target_table": target_table,
        },
        "files": {
            "raw_path": raw_path,
            "staging_path": staging_path,
            "quality_report_path": qr_path,
        },
        "record_stats": {
            "raw_count": raw_count,
            "staging_count": staging_count,
            "expected_write_count": expected_write_count,
        },
        "checksum": {"staging_sha256": sha256},
        "status": "ready",
    }


def gen_quality_report(staging_count: int) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "staging_count": staging_count,
        "quality_score": 1.0,
        "issues": [],
    }


def gen_raw_stub(count: int) -> dict:
    return {"record_count": count, "source": "e2e_mock", "generated_at": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# 1. Company (10 manifests, 1 record each)
# ---------------------------------------------------------------------------
def gen_company() -> list[dict]:
    results = []
    for idx, comp in enumerate(COMPANIES):
        job_id = f"e2e_company_{comp['code']}"
        raw_phys = f"{P_RAW}/{job_id}.json"
        staging_phys = f"{P_STAGING}/{job_id}.json"
        qr_phys = f"{P_QR}/{job_id}_quality_report.json"
        manifest_phys = f"{P_MANIFEST}/{job_id}.json"

        raw_log = f"{L_RAW}/{job_id}.json"
        staging_log = f"{L_STAGING}/{job_id}.json"
        qr_log = f"{L_QR}/{job_id}_quality_report.json"

        staging = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "company_master": {
                    "stock_code": comp["code"],
                    "stock_name": comp["name"],
                    "full_name": comp["full_name"],
                    "exchange": comp["exchange"],
                    "industry_level1": comp["industry"][:1],
                    "industry_level2": comp["industry"],
                    "listing_date": "2010-01-01",
                    "status": "active",
                    "source_type": "e2e_mock",
                },
                "company_profile": {
                    "stock_code": comp["code"],
                    "business_summary": f"{comp['name']}主营业务涵盖医药研发、生产与销售，是国内领先的医药企业。",
                    "main_segments_json": ["医药制造", "医疗器械", "研发服务"],
                    "market_position": f"{comp['name']}在细分行业中处于领先地位。",
                },
                "industries": [
                    {"industry_code": comp["industry"], "industry_name": "医药制造业"}
                ],
                "company_industries": [
                    {"stock_code": comp["code"], "industry_code": comp["industry"], "is_primary": True}
                ],
            },
        }
        sha256 = write_json(staging_phys, staging)
        write_json(raw_phys, gen_raw_stub(1))
        write_json(qr_phys, gen_quality_report(1))
        manifest = gen_manifest(
            job_id=job_id,
            category="company",
            endpoint="/api/ingest/company-package",
            ingest_package="company-package",
            ingest_field="company_master",
            target_table="company_master",
            raw_path=raw_log,
            staging_path=staging_log,
            qr_path=qr_log,
            raw_count=1,
            staging_count=1,
            expected_write_count=1,
            sha256=sha256,
        )
        write_json(manifest_phys, manifest)
        results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys})
    return results


# ---------------------------------------------------------------------------
# 2. Stock Daily (10 manifests, 90 records each = 900 total)
# ---------------------------------------------------------------------------
def gen_stock_daily() -> list[dict]:
    results = []
    start_date = datetime(2026, 1, 1)
    for comp in COMPANIES:
        job_id = f"e2e_stock_daily_{comp['code']}"
        raw_phys = f"{P_RAW}/{job_id}.json"
        staging_phys = f"{P_STAGING}/{job_id}.json"
        qr_phys = f"{P_QR}/{job_id}_quality_report.json"
        manifest_phys = f"{P_MANIFEST}/{job_id}.json"

        raw_log = f"{L_RAW}/{job_id}.json"
        staging_log = f"{L_STAGING}/{job_id}.json"
        qr_log = f"{L_QR}/{job_id}_quality_report.json"

        records = []
        base_price = random.uniform(20, 200)
        for i in range(90):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            open_p = round(base_price + random.uniform(-5, 5), 2)
            close_p = round(open_p + random.uniform(-3, 3), 2)
            high_p = round(max(open_p, close_p) + random.uniform(0, 2), 2)
            low_p = round(min(open_p, close_p) - random.uniform(0, 2), 2)
            records.append({
                "stock_code": comp["code"],
                "trade_date": date,
                "open_price": open_p,
                "close_price": close_p,
                "high_price": high_p,
                "low_price": low_p,
                "volume": random.randint(1000000, 50000000),
                "turnover": round(random.uniform(100000000, 5000000000), 2),
                "source_type": "e2e_mock",
            })

        staging = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "income_statements": [],
                "balance_sheets": [],
                "cashflow_statements": [],
                "financial_metrics": [],
                "financial_notes": [],
                "business_segments": [],
                "stock_daily": records,
                "sync_vector_index": False,
            },
        }
        sha256 = write_json(staging_phys, staging)
        write_json(raw_phys, gen_raw_stub(90))
        write_json(qr_phys, gen_quality_report(90))
        manifest = gen_manifest(
            job_id=job_id,
            category="stock_daily",
            endpoint="/api/ingest/financial-package",
            ingest_package="financial-package",
            ingest_field="stock_daily",
            target_table="stock_daily_hot",
            raw_path=raw_log,
            staging_path=staging_log,
            qr_path=qr_log,
            raw_count=90,
            staging_count=90,
            expected_write_count=90,
            sha256=sha256,
        )
        write_json(manifest_phys, manifest)
        results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys})
    return results


# ---------------------------------------------------------------------------
# 3. Announcement Raw (6 manifests, 20 records each = 120 total)
# ---------------------------------------------------------------------------
ANNOUNCEMENT_TEMPLATES = {
    "raw_announcements": [
        {"title": "2025年年度报告", "announcement_type": "定期报告"},
        {"title": "2025年年度业绩快报", "announcement_type": "业绩快报"},
        {"title": "2025年第三季度报告", "announcement_type": "定期报告"},
        {"title": "关于召开2025年度业绩说明会的公告", "announcement_type": "普通公告"},
    ],
    "structured_announcements": [
        {"category": "普通公告", "summary_text": "公司发布日常经营公告。", "signal_type": "neutral", "risk_level": "low"},
        {"category": "普通公告", "summary_text": "公司发布股东减持预披露公告。", "signal_type": "negative", "risk_level": "medium"},
        {"category": "普通公告", "summary_text": "公司发布回购股份公告。", "signal_type": "positive", "risk_level": "low"},
        {"category": "普通公告", "summary_text": "公司发布对外投资公告。", "signal_type": "neutral", "risk_level": "low"},
    ],
    "drug_approvals": [
        {"drug_name": "注射用卡瑞利珠单抗", "approval_type": "新药上市", "indication": "晚期肝细胞癌", "drug_stage": "已上市", "is_innovative_drug": 1, "review_status": "已通过", "market_scope": "国内"},
        {"drug_name": "马来酸吡咯替尼片", "approval_type": "新增适应症", "indication": "乳腺癌", "drug_stage": "已上市", "is_innovative_drug": 1, "review_status": "已通过", "market_scope": "国内"},
        {"drug_name": "甲苯磺酸瑞马唑仑", "approval_type": "新药上市", "indication": "麻醉镇静", "drug_stage": "已上市", "is_innovative_drug": 1, "review_status": "已通过", "market_scope": "国内"},
    ],
    "clinical_trials": [
        {"drug_name": "SHR-1316注射液", "trial_phase": "III期", "event_type": "入组完成", "indication": "小细胞肺癌", "summary_text": "III期临床试验完成患者入组。"},
        {"drug_name": "SHR-1701注射液", "trial_phase": "II期", "event_type": "获批临床", "indication": "晚期实体瘤", "summary_text": "获得国家药监局临床试验批准。"},
        {"drug_name": "SHR-1802注射液", "trial_phase": "I期", "event_type": "首例给药", "indication": "晚期恶性肿瘤", "summary_text": "I期临床试验完成首例患者给药。"},
    ],
    "procurement_events": [
        {"drug_name": "注射用卡瑞利珠单抗", "procurement_round": "国家医保谈判", "bid_result": "中选", "price_change_ratio": -0.35, "impact_summary": "成功进入国家医保目录，预计放量增长。"},
        {"drug_name": "马来酸吡咯替尼片", "procurement_round": "国家医保谈判", "bid_result": "中选", "price_change_ratio": -0.28, "impact_summary": "续约成功，维持医保支付标准。"},
        {"drug_name": "甲苯磺酸瑞马唑仑", "procurement_round": "国家医保谈判", "bid_result": "中选", "price_change_ratio": -0.22, "impact_summary": "首次纳入医保目录，有助于快速放量。"},
    ],
    "regulatory_risks": [
        {"risk_type": "药品不良反应", "risk_level": "medium", "summary_text": "国家药监局发布关于本品不良反应的警示信息。"},
        {"risk_type": "环保处罚", "risk_level": "low", "summary_text": "子公司收到地方环保局行政处罚决定书。"},
        {"risk_type": "临床试验暂停", "risk_level": "high", "summary_text": "某海外临床试验因安全性数据被监管机构要求暂停。"},
    ],
}


def pick_template(category: str, idx: int) -> dict:
    templates = ANNOUNCEMENT_TEMPLATES[category]
    return templates[idx % len(templates)].copy()


def gen_announcement_raw() -> list[dict]:
    results = []
    categories = ["raw_announcements", "structured_announcements", "drug_approvals",
                  "clinical_trials", "procurement_events", "regulatory_risks"]
    distributions = [
        [4, 3, 3, 3, 4, 3],
        [3, 4, 3, 3, 3, 4],
        [3, 3, 4, 3, 4, 3],
        [3, 3, 3, 4, 3, 4],
        [4, 3, 4, 3, 3, 3],
        [3, 4, 3, 4, 3, 3],
    ]
    for m_idx in range(6):
        job_id = f"e2e_announcement_raw_{m_idx+1:02d}"
        raw_phys = f"{P_RAW}/{job_id}.json"
        staging_phys = f"{P_STAGING}/{job_id}.json"
        qr_phys = f"{P_QR}/{job_id}_quality_report.json"
        manifest_phys = f"{P_MANIFEST}/{job_id}.json"

        raw_log = f"{L_RAW}/{job_id}.json"
        staging_log = f"{L_STAGING}/{job_id}.json"
        qr_log = f"{L_QR}/{job_id}_quality_report.json"

        payload = {cat: [] for cat in categories}
        payload["sync_vector_index"] = True

        for c_idx, cat in enumerate(categories):
            count = distributions[m_idx][c_idx]
            for i in range(count):
                tmpl = pick_template(cat, i + m_idx * 10)
                tmpl["stock_code"] = random.choice(STOCK_CODES)
                tmpl["source_type"] = "e2e_mock"
                tmpl["source_url"] = f"http://e2e.example.com/{cat}/{m_idx}_{i}"
                if cat == "raw_announcements":
                    tmpl["publish_date"] = (datetime(2026, 1, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
                    tmpl["exchange"] = random.choice(["SSE", "SZSE"])
                    tmpl["content"] = f"{tmpl['title']}内容详情..."
                elif cat == "structured_announcements":
                    tmpl["key_fields_json"] = {"key": "value"}
                elif cat in ("drug_approvals", "clinical_trials", "procurement_events", "regulatory_risks"):
                    tmpl["event_date"] = (datetime(2026, 1, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
                payload[cat].append(tmpl)

        staging = {"generated_at": datetime.now(timezone.utc).isoformat(), "payload": payload}
        total_records = sum(distributions[m_idx])
        sha256 = write_json(staging_phys, staging)
        write_json(raw_phys, gen_raw_stub(total_records))
        write_json(qr_phys, gen_quality_report(total_records))
        manifest = gen_manifest(
            job_id=job_id,
            category="announcement_raw",
            endpoint="/api/ingest/announcement-package",
            ingest_package="announcement-package",
            ingest_field="raw_announcements",
            target_table="announcement_raw_hot",
            raw_path=raw_log,
            staging_path=staging_log,
            qr_path=qr_log,
            raw_count=total_records,
            staging_count=total_records,
            expected_write_count=total_records,
            sha256=sha256,
        )
        write_json(manifest_phys, manifest)
        results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys, "records": total_records})
    return results


# ---------------------------------------------------------------------------
# 4. News Raw (4 manifests, 20 records each = 80 total)
# ---------------------------------------------------------------------------
NEWS_TITLES = {
    "company_research_report": [
        "{name}深度报告：创新药管线价值重估",
        "{name}季报点评：业绩符合预期，研发稳步推进",
        "{name}首次覆盖：生物药龙头，成长空间广阔",
        "{name}事件点评：核心产品获批，利好兑现",
        "{name}年度策略：国际化布局加速",
    ],
    "industry_news": [
        "创新药行业周报：医保谈判结果超预期",
        "医疗器械行业动态：集采政策趋于温和",
        "生物医药板块资金流向分析",
        "CXO行业跟踪：订单需求保持韧性",
    ],
    "policy_news": [
        "国家医保局发布新版医保目录调整方案",
        "CDE发布创新药审评审批改革意见",
        "国务院印发医药工业高质量发展行动计划",
        "国家药监局加强药品上市后变更管理",
    ],
    "company_news": [
        "{name}与海外药企达成战略合作",
        "{name}新一代抗体药物获批临床",
        "{name}生产基地通过FDA现场检查",
        "{name}发布股权激励计划",
    ],
}


def gen_news_raw() -> list[dict]:
    results = []
    per_manifest = {
        "company_research_report": [10, 10, 10, 10],
        "industry_news": [5, 5, 5, 5],
        "policy_news": [3, 2, 3, 2],
        "company_news": [2, 3, 2, 3],
    }

    counter = 0
    for m_idx in range(4):
        job_id = f"e2e_news_raw_{m_idx+1:02d}"
        raw_phys = f"{P_RAW}/{job_id}.json"
        staging_phys = f"{P_STAGING}/{job_id}.json"
        qr_phys = f"{P_QR}/{job_id}_quality_report.json"
        manifest_phys = f"{P_MANIFEST}/{job_id}.json"

        raw_log = f"{L_RAW}/{job_id}.json"
        staging_log = f"{L_STAGING}/{job_id}.json"
        qr_log = f"{L_QR}/{job_id}_quality_report.json"

        news_raw = []
        for ntype in ["company_research_report", "industry_news", "policy_news", "company_news"]:
            count = per_manifest[ntype][m_idx]
            titles = NEWS_TITLES[ntype]
            for i in range(count):
                counter += 1
                comp = random.choice(COMPANIES)
                title_tmpl = titles[i % len(titles)]
                title = title_tmpl.format(name=comp["name"]) if "{name}" in title_tmpl else title_tmpl
                news_raw.append({
                    "news_uid": f"e2e_news_{counter:04d}",
                    "title": title,
                    "publish_time": (datetime(2026, 1, 1, 8, 0, 0) + timedelta(days=random.randint(0, 90), hours=random.randint(0, 12))).isoformat(),
                    "source_name": "E2E Mock News",
                    "source_url": f"http://e2e.example.com/news/{counter}",
                    "author_name": "E2E Author",
                    "content": f"{title}详细内容...",
                    "news_type": ntype,
                    "language": "zh",
                })

        staging = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "macro_indicators": [],
                "news_raw": news_raw,
                "news_structured": [],
                "news_industry_maps": {},
                "news_company_maps": {},
                "industry_impact_events": [],
                "sync_vector_index": True,
            },
        }
        sha256 = write_json(staging_phys, staging)
        write_json(raw_phys, gen_raw_stub(20))
        write_json(qr_phys, gen_quality_report(20))
        manifest = gen_manifest(
            job_id=job_id,
            category="research_report",
            endpoint="/api/ingest/news-package",
            ingest_package="news-package",
            ingest_field="news_raw",
            target_table="news_raw_hot",
            raw_path=raw_log,
            staging_path=staging_log,
            qr_path=qr_log,
            raw_count=20,
            staging_count=20,
            expected_write_count=20,
            sha256=sha256,
        )
        write_json(manifest_phys, manifest)
        results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys, "records": 20})
    return results


# ---------------------------------------------------------------------------
# 5. Macro (2 manifests, 12 records each = 24 total)
# ---------------------------------------------------------------------------
MACRO_INDICATORS = [
    {"indicator_name": "GDP", "unit": "%"},
    {"indicator_name": "CPI", "unit": "%"},
    {"indicator_name": "PPI", "unit": "%"},
    {"indicator_name": "PMI", "unit": "指数"},
    {"indicator_name": "M2", "unit": "万亿元"},
    {"indicator_name": "社会消费品零售总额", "unit": "亿元"},
    {"indicator_name": "固定资产投资", "unit": "%"},
    {"indicator_name": "进出口总额", "unit": "亿美元"},
    {"indicator_name": "失业率", "unit": "%"},
    {"indicator_name": "工业增加值", "unit": "%"},
    {"indicator_name": "LPR_1Y", "unit": "%"},
    {"indicator_name": "LPR_5Y", "unit": "%"},
]


def gen_macro() -> list[dict]:
    results = []
    for m_idx in range(2):
        job_id = f"e2e_macro_{m_idx+1:02d}"
        raw_phys = f"{P_RAW}/{job_id}.json"
        staging_phys = f"{P_STAGING}/{job_id}.json"
        qr_phys = f"{P_QR}/{job_id}_quality_report.json"
        manifest_phys = f"{P_MANIFEST}/{job_id}.json"

        raw_log = f"{L_RAW}/{job_id}.json"
        staging_log = f"{L_STAGING}/{job_id}.json"
        qr_log = f"{L_QR}/{job_id}_quality_report.json"

        records = []
        for i in range(12):
            ind = MACRO_INDICATORS[i]
            records.append({
                "indicator_name": ind["indicator_name"],
                "period": f"2026-Q{(i % 4) + 1}",
                "value": round(random.uniform(1.0, 12.0), 2),
                "unit": ind["unit"],
                "source_type": "e2e_mock",
                "source_url": f"http://e2e.example.com/macro/{ind['indicator_name']}",
            })

        staging = {"generated_at": datetime.now(timezone.utc).isoformat(), "records": records}
        sha256 = write_json(staging_phys, staging)
        write_json(raw_phys, gen_raw_stub(12))
        write_json(qr_phys, gen_quality_report(12))
        manifest = gen_manifest(
            job_id=job_id,
            category="macro",
            endpoint="/api/ingest/macro-package",
            ingest_package="macro-package",
            ingest_field="macro_indicators",
            target_table="macro_indicator_hot",
            raw_path=raw_log,
            staging_path=staging_log,
            qr_path=qr_log,
            raw_count=12,
            staging_count=12,
            expected_write_count=12,
            sha256=sha256,
        )
        write_json(manifest_phys, manifest)
        results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys, "records": 12})
    return results


# ---------------------------------------------------------------------------
# 6. Patent (1 manifest, 50 records, SKIP_INGEST)
# ---------------------------------------------------------------------------
def gen_patent() -> list[dict]:
    results = []
    job_id = "e2e_patent_001"
    raw_phys = f"{P_RAW}/{job_id}.json"
    staging_phys = f"{P_STAGING}/{job_id}.json"
    qr_phys = f"{P_QR}/{job_id}_quality_report.json"
    manifest_phys = f"{P_MANIFEST}/{job_id}.json"

    raw_log = f"{L_RAW}/{job_id}.json"
    staging_log = f"{L_STAGING}/{job_id}.json"
    qr_log = f"{L_QR}/{job_id}_quality_report.json"

    records = []
    for i in range(50):
        records.append({
            "patent_id": f"CN2026E2E{i+1:04d}",
            "title": f"E2E测试专利{i+1}: 一种医药化合物及其制备方法",
            "applicant": random.choice([c["name"] for c in COMPANIES]),
            "application_date": (datetime(2026, 1, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
        })

    staging = {"generated_at": datetime.now(timezone.utc).isoformat(), "records": records}
    sha256 = write_json(staging_phys, staging)
    write_json(raw_phys, gen_raw_stub(50))
    write_json(qr_phys, gen_quality_report(50))
    manifest = gen_manifest(
        job_id=job_id,
        category="patent",
        endpoint="/api/ingest/patent-package",
        ingest_package="patent-package",
        ingest_field="patent",
        target_table="patent_hot",
        raw_path=raw_log,
        staging_path=staging_log,
        qr_path=qr_log,
        raw_count=50,
        staging_count=50,
        expected_write_count=0,
        sha256=sha256,
    )
    write_json(manifest_phys, manifest)
    results.append({"job_id": job_id, "manifest": manifest_phys, "staging": staging_phys, "records": 50})
    return results


def main():
    print("Generating E2E test set...")
    company_results = gen_company()
    stock_results = gen_stock_daily()
    ann_results = gen_announcement_raw()
    news_results = gen_news_raw()
    macro_results = gen_macro()
    patent_results = gen_patent()

    all_manifests = company_results + stock_results + ann_results + news_results + macro_results + patent_results

    print(f"\nTotal manifests: {len(all_manifests)}")
    print(f"  company:          {len(company_results)} manifests, 10 records")
    print(f"  stock_daily:      {len(stock_results)} manifests, 900 records")
    print(f"  announcement_raw: {len(ann_results)} manifests, 120 records")
    print(f"  news_raw:         {len(news_results)} manifests, 80 records")
    print(f"  macro:            {len(macro_results)} manifests, 24 records")
    print(f"  patent:           {len(patent_results)} manifests, 50 records")

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest_center.manifest_model import parse_manifest
    ok = True
    for item in all_manifests:
        try:
            parse_manifest(item["manifest"])
        except Exception as exc:
            print(f"  FAIL: {item['manifest']} -> {exc}")
            ok = False
    print(f"\nAll manifests valid: {'YES' if ok else 'NO'}")


if __name__ == "__main__":
    main()
