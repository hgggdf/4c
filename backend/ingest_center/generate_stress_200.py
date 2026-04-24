"""
Generate stress_200 test data for 4-layer pipeline.

Usage:
    python -m ingest_center.generate_stress_200
"""
import json
import hashlib
import os
import random
from datetime import datetime, timezone, timedelta

random.seed(42)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRESS_NAME = "stress_200"

MANIFEST_DIR = os.path.join(PROJECT_ROOT, "ingest_center", f"manifests_{STRESS_NAME}")
STAGING_DIR = os.path.join(PROJECT_ROOT, "crawler", "staging", STRESS_NAME)
RAW_DIR = os.path.join(PROJECT_ROOT, "crawler", "raw", STRESS_NAME)
QR_DIR = os.path.join(PROJECT_ROOT, "crawler", "staging", "quality_reports", STRESS_NAME)

for d in [MANIFEST_DIR, STAGING_DIR, RAW_DIR, QR_DIR]:
    os.makedirs(d, exist_ok=True)

# 200 stock codes (avoid overlap with e2e pool: 002007,300015,300122,300760,600161,600196,600276,603259,688271,688363)
STOCK_CODES = [f"{600000 + i:06d}" for i in range(200)]
INDUSTRY_CODES = ["C27", "C35", "C26", "C28", "C36", "C37", "C39", "C40", "I64", "I65"]
EXCHANGES = ["SZSE", "SSE"]
COMPANY_NAMES = [f"Stress公司{i:03d}" for i in range(200)]

ANN_TYPES = ["年度报告", "业绩快报", "临时公告", "普通公告"]
SIGNAL_TYPES = ["positive", "negative", "neutral"]
RISK_LEVELS = ["low", "medium", "high"]
NEWS_TYPES = ["company_research_report", "industry_news", "policy_news"]
LANGUAGES = ["zh"]
DRUG_NAMES = ["阿莫西林胶囊", "注射用头孢", "盐酸二甲双胍片", "布洛芬缓释胶囊", "连花清瘟胶囊"]
APPROVAL_TYPES = ["新药上市", "仿制药一致性评价", "新增适应症"]
TRIAL_PHASES = ["I期", "II期", "III期", "IV期"]
PROCUREMENT_ROUNDS = ["国采第一批", "国采第二批", "国采第三批"]
BID_RESULTS = ["中标", "未中标", "备选"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_manifest(job_id, data_category, endpoint, ingest_package, ingest_field, target_table,
                  raw_path, staging_path, quality_report_path,
                  raw_count, staging_count, expected_write_count, staging_sha256):
    return {
        "spec_version": "1.0",
        "staging_format_version": "1.0",
        "job_id": job_id,
        "created_at": now_iso(),
        "producer": {
            "system": "openclaw",
            "module": "Stress200Generator",
            "run_id": f"run_{STRESS_NAME}_{job_id}"
        },
        "data_category": data_category,
        "time_window": {
            "begin_date": "2026-01-01",
            "end_date": "2026-03-31"
        },
        "target": {
            "endpoint": endpoint,
            "ingest_package": ingest_package,
            "ingest_field": ingest_field,
            "target_table": target_table
        },
        "files": {
            "raw_path": raw_path,
            "staging_path": staging_path,
            "quality_report_path": quality_report_path
        },
        "record_stats": {
            "raw_count": raw_count,
            "staging_count": staging_count,
            "expected_write_count": expected_write_count
        },
        "checksum": {
            "staging_sha256": staging_sha256
        },
        "status": "ready"
    }


def generate_company():
    print("[GEN] company ...")
    total = 0
    for idx, stock_code in enumerate(STOCK_CODES):
        stock_name = COMPANY_NAMES[idx]
        full_name = f"{stock_name}股份有限公司"
        exchange = EXCHANGES[idx % 2]
        industry_code = INDUSTRY_CODES[idx % len(INDUSTRY_CODES)]

        # staging
        staging = {
            "generated_at": now_iso(),
            "payload": {
                "company_master": {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "full_name": full_name,
                    "exchange": exchange,
                    "industry_level1": industry_code[0],
                    "industry_level2": industry_code,
                    "listing_date": "2010-01-01",
                    "status": "active",
                    "source_type": "stress_mock"
                },
                "company_profile": {
                    "stock_code": stock_code,
                    "business_summary": f"{stock_name}主营业务涵盖医药研发、生产制造及销售。",
                    "main_segments_json": ["医药制造", "医疗器械", "研发服务"],
                    "market_position": f"{stock_name}在细分领域具有较强竞争力。"
                },
                "industries": [
                    {
                        "industry_code": industry_code,
                        "industry_name": f"{industry_code}行业"
                    }
                ],
                "company_industries": [
                    {
                        "stock_code": stock_code,
                        "industry_code": industry_code,
                        "is_primary": True
                    }
                ]
            }
        }
        job_id = f"{STRESS_NAME}_company_{stock_code}"
        staging_name = f"{job_id}.json"
        staging_path = os.path.join(STAGING_DIR, staging_name)
        write_json(staging_path, staging)
        sha = sha256_file(staging_path)

        # raw
        raw = {
            "record_count": 1,
            "source": "stress_mock",
            "generated_at": now_iso()
        }
        raw_path = os.path.join(RAW_DIR, staging_name)
        write_json(raw_path, raw)

        # quality report
        qr = {
            "generated_at": now_iso(),
            "staging_count": 1,
            "quality_score": 1.0,
            "issues": []
        }
        qr_name = f"{job_id}_quality_report.json"
        qr_path = os.path.join(QR_DIR, qr_name)
        write_json(qr_path, qr)

        # manifest
        manifest = make_manifest(
            job_id=job_id,
            data_category="company",
            endpoint="/api/ingest/company-package",
            ingest_package="company-package",
            ingest_field="company_master",
            target_table="company_master",
            raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
            staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
            quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
            raw_count=1,
            staging_count=1,
            expected_write_count=1,
            staging_sha256=sha
        )
        write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
        total += 1
    print(f"[GEN] company done: {total} manifests")


def generate_stock_daily():
    print("[GEN] stock_daily ...")
    total = 0
    total_records = 0
    for idx, stock_code in enumerate(STOCK_CODES):
        job_id = f"{STRESS_NAME}_stock_daily_{stock_code}"
        staging_name = f"{job_id}.json"

        stock_daily_items = []
        base_date = datetime(2026, 1, 1)
        for day in range(30):
            trade_date = (base_date + timedelta(days=day)).strftime("%Y-%m-%d")
            open_price = round(random.uniform(50, 150), 2)
            close_price = round(open_price * random.uniform(0.9, 1.1), 2)
            high_price = round(max(open_price, close_price) * random.uniform(1.0, 1.05), 2)
            low_price = round(min(open_price, close_price) * random.uniform(0.95, 1.0), 2)
            volume = int(random.uniform(1_000_000, 50_000_000))
            turnover = round(volume * close_price, 2)
            stock_daily_items.append({
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": open_price,
                "close_price": close_price,
                "high_price": high_price,
                "low_price": low_price,
                "volume": volume,
                "turnover": turnover,
                "source_type": "stress_mock"
            })

        staging = {
            "generated_at": now_iso(),
            "payload": {
                "income_statements": [],
                "balance_sheets": [],
                "cashflow_statements": [],
                "financial_metrics": [],
                "financial_notes": [],
                "business_segments": [],
                "stock_daily": stock_daily_items,
                "sync_vector_index": False
            }
        }
        staging_path = os.path.join(STAGING_DIR, staging_name)
        write_json(staging_path, staging)
        sha = sha256_file(staging_path)

        raw = {
            "record_count": 30,
            "source": "stress_mock",
            "generated_at": now_iso()
        }
        write_json(os.path.join(RAW_DIR, staging_name), raw)

        qr = {
            "generated_at": now_iso(),
            "staging_count": 30,
            "quality_score": 1.0,
            "issues": []
        }
        qr_name = f"{job_id}_quality_report.json"
        write_json(os.path.join(QR_DIR, qr_name), qr)

        manifest = make_manifest(
            job_id=job_id,
            data_category="stock_daily",
            endpoint="/api/ingest/financial-package",
            ingest_package="financial-package",
            ingest_field="stock_daily",
            target_table="stock_daily",
            raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
            staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
            quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
            raw_count=30,
            staging_count=30,
            expected_write_count=30,
            staging_sha256=sha
        )
        write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
        total += 1
        total_records += 30
    print(f"[GEN] stock_daily done: {total} manifests, {total_records} records")


def generate_announcement_raw():
    print("[GEN] announcement_raw ...")
    total_manifests = 0
    total_raw = 0
    num_manifests = 40
    items_per_manifest = 15
    total_items = num_manifests * items_per_manifest

    all_raw_items = []
    for i in range(total_items):
        stock_code = STOCK_CODES[i % len(STOCK_CODES)]
        ann_type = ANN_TYPES[i % len(ANN_TYPES)]
        title = f"{stock_code}公司{i+1}号公告: {ann_type}"
        publish_date = (datetime(2026, 1, 1) + timedelta(days=i % 90)).strftime("%Y-%m-%d")
        all_raw_items.append({
            "title": title,
            "announcement_type": ann_type,
            "stock_code": stock_code,
            "source_type": "stress_mock",
            "source_url": f"http://stress.example.com/raw_announcements/{i}",
            "publish_date": publish_date,
            "exchange": EXCHANGES[i % 2],
            "content": f"{title}详细内容..."
        })

    for m in range(num_manifests):
        start = m * items_per_manifest
        end = start + items_per_manifest
        raw_items = all_raw_items[start:end]

        # L3 fields
        structured_items = []
        drug_approval_items = []
        clinical_trial_items = []
        procurement_items = []
        regulatory_risk_items = []

        for i, raw in enumerate(raw_items):
            idx = start + i
            stock_code = raw["stock_code"]
            title = raw["title"]
            publish_date = raw["publish_date"]
            ann_type = raw["announcement_type"]

            structured_items.append({
                "category": ann_type if ann_type != "临时公告" else "普通公告",
                "summary_text": f"{stock_code}发布{ann_type}。",
                "signal_type": SIGNAL_TYPES[idx % 3],
                "risk_level": RISK_LEVELS[idx % 3],
                "stock_code": stock_code,
                "title": title,
                "publish_date": publish_date,
                "key_fields_json": {"key": f"value_{idx}"}
            })

            drug_approval_items.append({
                "stock_code": stock_code,
                "drug_name": DRUG_NAMES[idx % len(DRUG_NAMES)],
                "approval_type": APPROVAL_TYPES[idx % len(APPROVAL_TYPES)],
                "approval_date": publish_date,
                "indication": "适应症描述",
                "drug_stage": "已上市",
                "is_innovative_drug": 1 if idx % 2 == 0 else 0,
                "review_status": "已通过",
                "market_scope": "国内",
                "source_announcement_id": None,
                "source_type": "stress_mock",
                "source_url": f"http://stress.example.com/drug_approvals/{idx}",
            })

            clinical_trial_items.append({
                "stock_code": stock_code,
                "drug_name": DRUG_NAMES[(idx + 1) % len(DRUG_NAMES)],
                "trial_phase": TRIAL_PHASES[idx % len(TRIAL_PHASES)],
                "event_type": "临床进展",
                "event_date": publish_date,
                "indication": "适应症描述",
                "summary_text": f"{stock_code}临床试验进展摘要。",
                "source_announcement_id": None,
                "source_type": "stress_mock",
                "source_url": f"http://stress.example.com/clinical_trials/{idx}",
            })

            procurement_items.append({
                "stock_code": stock_code,
                "drug_name": DRUG_NAMES[(idx + 2) % len(DRUG_NAMES)],
                "procurement_round": PROCUREMENT_ROUNDS[idx % len(PROCUREMENT_ROUNDS)],
                "bid_result": BID_RESULTS[idx % len(BID_RESULTS)],
                "price_change_ratio": round(random.uniform(-0.5, 0.5), 4),
                "event_date": publish_date,
                "impact_summary": f"{stock_code}集采影响摘要。",
                "source_announcement_id": None,
                "source_type": "stress_mock",
                "source_url": f"http://stress.example.com/procurement/{idx}",
            })

            regulatory_risk_items.append({
                "stock_code": stock_code,
                "risk_type": "监管问询",
                "event_date": publish_date,
                "risk_level": RISK_LEVELS[idx % 3],
                "summary_text": f"{stock_code}监管风险摘要。",
                "source_announcement_id": None,
                "source_type": "stress_mock",
                "source_url": f"http://stress.example.com/regulatory/{idx}",
            })

        staging = {
            "generated_at": now_iso(),
            "payload": {
                "raw_announcements": raw_items,
                "structured_announcements": structured_items,
                "drug_approvals": drug_approval_items,
                "clinical_trials": clinical_trial_items,
                "procurement_events": procurement_items,
                "regulatory_risks": regulatory_risk_items,
                "sync_vector_index": True
            }
        }

        # IMPORTANT: staging file name must match e2e_announcement_raw_*.json for run_announcement_l3.py
        staging_name = f"e2e_announcement_raw_{m+1:02d}.json"
        staging_path = os.path.join(STAGING_DIR, staging_name)
        write_json(staging_path, staging)
        sha = sha256_file(staging_path)

        raw = {
            "record_count": items_per_manifest,
            "source": "stress_mock",
            "generated_at": now_iso()
        }
        write_json(os.path.join(RAW_DIR, staging_name), raw)

        qr = {
            "generated_at": now_iso(),
            "staging_count": items_per_manifest,
            "quality_score": 1.0,
            "issues": []
        }
        qr_name = f"e2e_announcement_raw_{m+1:02d}_quality_report.json"
        write_json(os.path.join(QR_DIR, qr_name), qr)

        job_id = f"{STRESS_NAME}_announcement_raw_{m+1:02d}"
        manifest = make_manifest(
            job_id=job_id,
            data_category="announcement_raw",
            endpoint="/api/ingest/announcement-package",
            ingest_package="announcement-package",
            ingest_field="raw_announcements",
            target_table="announcement_raw_hot",
            raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
            staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
            quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
            raw_count=items_per_manifest,
            staging_count=items_per_manifest,
            expected_write_count=items_per_manifest,
            staging_sha256=sha
        )
        write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
        total_manifests += 1
        total_raw += items_per_manifest

    print(f"[GEN] announcement_raw done: {total_manifests} manifests, {total_raw} records")


def generate_research_report():
    print("[GEN] research_report ...")
    total_manifests = 0
    total_raw = 0
    num_manifests = 40
    items_per_manifest = 10
    total_items = num_manifests * items_per_manifest

    all_news_items = []
    for i in range(total_items):
        news_uid = f"stress_news_{i+1:04d}"
        stock_code = STOCK_CODES[i % len(STOCK_CODES)]
        publish_time = (datetime(2026, 1, 1) + timedelta(days=i % 90, hours=i % 24)).strftime("%Y-%m-%dT%H:%M:%S")
        all_news_items.append({
            "news_uid": news_uid,
            "title": f"Stress新闻{i+1}: {stock_code}行业动态",
            "publish_time": publish_time,
            "source_name": "Stress Mock News",
            "source_url": f"http://stress.example.com/news/{i+1}",
            "author_name": "Stress Author",
            "content": f"Stress新闻{i+1}详细内容...",
            "news_type": NEWS_TYPES[i % len(NEWS_TYPES)],
            "language": "zh"
        })

    for m in range(num_manifests):
        start = m * items_per_manifest
        end = start + items_per_manifest
        news_items = all_news_items[start:end]

        # L3 fields
        news_structured = []
        news_industry_maps = {}
        news_company_maps = {}
        industry_impact_events = []

        for i, news in enumerate(news_items):
            idx = start + i
            news_uid = news["news_uid"]
            stock_code = news["title"].split(":")[0].replace("Stress新闻", "").strip()
            stock_code = STOCK_CODES[idx % len(STOCK_CODES)]
            industry_code = INDUSTRY_CODES[idx % len(INDUSTRY_CODES)]

            news_structured.append({
                "topic_category": "行业动态",
                "summary_text": f"{news['title']}摘要。",
                "keywords_json": ["医药", "行业", "动态"],
                "signal_type": SIGNAL_TYPES[idx % 3],
                "impact_level": "medium",
                "impact_horizon": "short",
                "sentiment_label": "neutral",
                "confidence_score": round(random.uniform(0.7, 0.99), 2),
                "news_uid": news_uid,
            })

            strength_val = 0.6 if idx % 3 == 0 else (0.3 if idx % 3 == 1 else 0.9)
            news_industry_maps[news_uid] = [{
                "industry_code": industry_code,
                "impact_direction": "positive" if idx % 2 == 0 else "negative",
                "impact_strength": strength_val,
                "reason_text": f"新闻{news_uid}对{industry_code}行业的影响。"
            }]

            news_company_maps[news_uid] = [{
                "stock_code": stock_code,
                "impact_direction": "positive" if idx % 2 == 0 else "negative",
                "impact_strength": strength_val,
                "reason_text": f"新闻{news_uid}对{stock_code}的影响。"
            }]

            industry_impact_events.append({
                "industry_code": industry_code,
                "event_name": f"事件{news_uid}",
                "impact_direction": "positive" if idx % 2 == 0 else "negative",
                "impact_level": "medium",
                "impact_horizon": "short",
                "summary_text": f"行业影响事件{news_uid}摘要。",
                "event_date": news["publish_time"][:10],
                "news_uid": news_uid,
            })

        staging = {
            "generated_at": now_iso(),
            "payload": {
                "macro_indicators": [],
                "news_raw": news_items,
                "news_structured": news_structured,
                "news_industry_maps": news_industry_maps,
                "news_company_maps": news_company_maps,
                "industry_impact_events": industry_impact_events,
                "sync_vector_index": True
            }
        }

        # IMPORTANT: staging file name must match e2e_news_raw_*.json for run_news_l3.py
        staging_name = f"e2e_news_raw_{m+1:02d}.json"
        staging_path = os.path.join(STAGING_DIR, staging_name)
        write_json(staging_path, staging)
        sha = sha256_file(staging_path)

        raw = {
            "record_count": items_per_manifest,
            "source": "stress_mock",
            "generated_at": now_iso()
        }
        write_json(os.path.join(RAW_DIR, staging_name), raw)

        qr = {
            "generated_at": now_iso(),
            "staging_count": items_per_manifest,
            "quality_score": 1.0,
            "issues": []
        }
        qr_name = f"e2e_news_raw_{m+1:02d}_quality_report.json"
        write_json(os.path.join(QR_DIR, qr_name), qr)

        job_id = f"{STRESS_NAME}_research_report_{m+1:02d}"
        manifest = make_manifest(
            job_id=job_id,
            data_category="research_report",
            endpoint="/api/ingest/news-package",
            ingest_package="news-package",
            ingest_field="news_raw",
            target_table="news_raw_hot",
            raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
            staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
            quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
            raw_count=items_per_manifest,
            staging_count=items_per_manifest,
            expected_write_count=items_per_manifest,
            staging_sha256=sha
        )
        write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
        total_manifests += 1
        total_raw += items_per_manifest

    print(f"[GEN] research_report done: {total_manifests} manifests, {total_raw} records")


def generate_macro():
    print("[GEN] macro ...")
    indicators = [
        ("GDP", "%"), ("CPI", "%"), ("PPI", "%"), ("PMI", "指数"),
        ("M2", "万亿元"), ("社会消费品零售总额", "亿元"), ("固定资产投资", "%"),
        ("出口总额", "万亿元"), ("失业率", "%"), ("工业增加值", "%"),
        ("LPR_1Y", "%"), ("LPR_5Y", "%")
    ]
    total_manifests = 0
    for m in range(2):
        records = []
        for i, (name, unit) in enumerate(indicators):
            records.append({
                "indicator_name": name,
                "period": f"2026-Q{(i % 4) + 1}",
                "value": round(random.uniform(1, 15), 2),
                "unit": unit,
                "source_type": "stress_mock",
                "source_url": f"http://stress.example.com/macro/{name}"
            })

        staging = {
            "generated_at": now_iso(),
            "records": records
        }
        staging_name = f"{STRESS_NAME}_macro_{m+1:02d}.json"
        staging_path = os.path.join(STAGING_DIR, staging_name)
        write_json(staging_path, staging)
        sha = sha256_file(staging_path)

        raw = {
            "record_count": len(indicators),
            "source": "stress_mock",
            "generated_at": now_iso()
        }
        write_json(os.path.join(RAW_DIR, staging_name), raw)

        qr = {
            "generated_at": now_iso(),
            "staging_count": len(indicators),
            "quality_score": 1.0,
            "issues": []
        }
        qr_name = f"{STRESS_NAME}_macro_{m+1:02d}_quality_report.json"
        write_json(os.path.join(QR_DIR, qr_name), qr)

        job_id = f"{STRESS_NAME}_macro_{m+1:02d}"
        manifest = make_manifest(
            job_id=job_id,
            data_category="macro",
            endpoint="/api/macro-write/macro-indicators",
            ingest_package="macro-package",
            ingest_field="macro_indicators",
            target_table="macro_indicator_hot",
            raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
            staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
            quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
            raw_count=len(indicators),
            staging_count=len(indicators),
            expected_write_count=len(indicators),
            staging_sha256=sha
        )
        write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
        total_manifests += 1
    print(f"[GEN] macro done: {total_manifests} manifests")


def generate_patent():
    print("[GEN] patent ...")
    records = []
    for i in range(50):
        records.append({
            "patent_id": f"CN2026STRESS{i+1:04d}",
            "title": f"Stress专利{i+1}: 一种医药化合物及其制备方法",
            "applicant": COMPANY_NAMES[i % len(COMPANY_NAMES)],
            "application_date": (datetime(2026, 1, 1) + timedelta(days=i % 90)).strftime("%Y-%m-%d")
        })

    staging = {
        "generated_at": now_iso(),
        "records": records
    }
    staging_name = f"{STRESS_NAME}_patent_001.json"
    staging_path = os.path.join(STAGING_DIR, staging_name)
    write_json(staging_path, staging)
    sha = sha256_file(staging_path)

    raw = {
        "record_count": 50,
        "source": "stress_mock",
        "generated_at": now_iso()
    }
    write_json(os.path.join(RAW_DIR, staging_name), raw)

    qr = {
        "generated_at": now_iso(),
        "staging_count": 50,
        "quality_score": 1.0,
        "issues": []
    }
    qr_name = f"{STRESS_NAME}_patent_001_quality_report.json"
    write_json(os.path.join(QR_DIR, qr_name), qr)

    job_id = f"{STRESS_NAME}_patent_001"
    manifest = make_manifest(
        job_id=job_id,
        data_category="patent",
        endpoint="/api/ingest/patent-package",
        ingest_package="patent-package",
        ingest_field="patent",
        target_table="patent_hot",
        raw_path=f"backend/crawler/raw/{STRESS_NAME}/{staging_name}",
        staging_path=f"backend/crawler/staging/{STRESS_NAME}/{staging_name}",
        quality_report_path=f"backend/crawler/staging/quality_reports/{STRESS_NAME}/{qr_name}",
        raw_count=50,
        staging_count=50,
        expected_write_count=0,
        staging_sha256=sha
    )
    write_json(os.path.join(MANIFEST_DIR, f"{job_id}.json"), manifest)
    print("[GEN] patent done: 1 manifest")


def verify_manifests():
    print("[VERIFY] manifests ...")
    from ingest_center import manifest_model
    ok = 0
    fail = 0
    for entry in os.listdir(MANIFEST_DIR):
        if not entry.endswith(".json"):
            continue
        path = os.path.join(MANIFEST_DIR, entry)
        try:
            manifest_model.parse_manifest(path)
            ok += 1
        except Exception as exc:
            print(f"  [FAIL] {entry}: {exc}")
            fail += 1
    print(f"[VERIFY] done: {ok} passed, {fail} failed")
    return fail == 0


def main():
    generate_company()
    generate_stock_daily()
    generate_announcement_raw()
    generate_research_report()
    generate_macro()
    generate_patent()
    if verify_manifests():
        print("\n[OK] All stress_200 data generated and verified.")
    else:
        print("\n[ERROR] Some manifests failed verification.")


if __name__ == "__main__":
    main()
