from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.core.database.models.company import Company
from app.core.database.models.news_hot import NewsRawHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.session import SessionLocal
from app.core.utils.dedup import prepare_dedup_record
from app.knowledge import sync
from app.knowledge.store import get_vector_store


MARKER = "[SYNTHETIC_VECTOR_DATA]"
STOCK_CODE = "600276"


def _ensure_company(db) -> None:
    company = db.get(Company, STOCK_CODE)
    if company is not None:
        return
    db.add(
        Company(
            stock_code=STOCK_CODE,
            stock_name="恒瑞医药",
            full_name="江苏恒瑞医药股份有限公司",
            exchange="SH",
            industry_level1="医药生物",
            business_summary=f"{MARKER} 合成公司画像：用于向量库测试，不代表真实投资信息。",
        )
    )
    db.flush()


def _upsert_by_dedup(db, model, data_type: str, payload: dict[str, Any], uid_field: str):
    prepared = prepare_dedup_record(data_type, payload)
    existing = db.execute(
        select(model).where(model.dedup_key == prepared["dedup_key"])
    ).scalars().first()
    if existing is None:
        existing = db.execute(
            select(model).where(getattr(model, uid_field) == prepared[uid_field])
        ).scalars().first()

    if existing is None:
        row = model(**prepared)
        db.add(row)
        db.flush()
        return row, True

    for key, value in prepared.items():
        if key != "id" and hasattr(existing, key):
            setattr(existing, key, value)
    db.flush()
    return existing, False


def _synthetic_news_rows() -> list[dict[str, Any]]:
    return [
        {
            "news_uid": "synthetic-vector-news-600276-global-bd",
            "title": f"{MARKER} 恒瑞医药国际化合作测试新闻",
            "publish_time": datetime(2026, 5, 25, 9, 30, 0),
            "source_name": "synthetic_test",
            "source_url": "https://synthetic.local/vector/news/600276/global-bd",
            "news_type": "synthetic_test",
            "content": (
                f"{MARKER} 这是一条合成新闻，用于测试向量库、检索服务和 AI Agent。"
                "内容描述恒瑞医药与海外药企开展创新药授权合作，市场关注国际化收入、里程碑付款和研发管线兑现。"
            ),
            "summary_text": f"{MARKER} 合成新闻摘要：创新药国际化合作。",
            "related_stock_codes_json": [STOCK_CODE],
            "related_industry_codes_json": ["SYNTHETIC_MED"],
            "key_fields_json": {
                "signal_type": "synthetic_positive_event",
                "impact_level": "medium",
                "impact_direction": "positive",
                "impact_horizon": "medium_term",
            },
            "file_type": "synthetic",
            "original_filename": "synthetic_news_global_bd.json",
        },
        {
            "news_uid": "synthetic-vector-news-600276-rd-progress",
            "title": f"{MARKER} 恒瑞医药研发管线进展测试新闻",
            "publish_time": datetime(2026, 5, 25, 10, 0, 0),
            "source_name": "synthetic_test",
            "source_url": "https://synthetic.local/vector/news/600276/rd-progress",
            "news_type": "synthetic_test",
            "content": (
                f"{MARKER} 这是一条合成新闻，用于补齐 news 向量数据。"
                "内容描述 ADC、GLP-1 和肿瘤免疫管线推进，方便测试新闻语义检索和事件证据回表。"
            ),
            "summary_text": f"{MARKER} 合成新闻摘要：研发管线推进。",
            "related_stock_codes_json": [STOCK_CODE],
            "related_industry_codes_json": ["SYNTHETIC_MED"],
            "key_fields_json": {
                "signal_type": "synthetic_rd_progress",
                "impact_level": "low",
                "impact_direction": "neutral_positive",
                "impact_horizon": "long_term",
            },
            "file_type": "synthetic",
            "original_filename": "synthetic_news_rd_progress.json",
        },
    ]


def _synthetic_report_rows() -> list[dict[str, Any]]:
    return [
        {
            "report_uid": "synthetic-vector-report-600276-valuation",
            "scope_type": "company",
            "stock_code": STOCK_CODE,
            "industry_code": None,
            "title": f"{MARKER} 恒瑞医药估值与创新药管线测试研报",
            "publish_date": date(2026, 5, 25),
            "report_org": "synthetic_test",
            "content": (
                f"{MARKER} 这是一篇合成研报，用于测试 research_report 向量库。"
                "研报假设公司创新药收入增长、研发费用率维持高位，并讨论 PE、DCF、现金流和安全边际。"
            ),
            "summary_text": f"{MARKER} 合成研报摘要：估值与创新药管线。",
            "source_type": "synthetic",
            "source_url": "https://synthetic.local/vector/report/600276/valuation",
            "file_type": "synthetic",
            "original_filename": "synthetic_report_valuation.txt",
        },
        {
            "report_uid": "synthetic-vector-report-600276-risk",
            "scope_type": "company",
            "stock_code": STOCK_CODE,
            "industry_code": None,
            "title": f"{MARKER} 恒瑞医药政策风险与量价异动测试研报",
            "publish_date": date(2026, 5, 25),
            "report_org": "synthetic_test",
            "content": (
                f"{MARKER} 这是一篇合成研报，用于测试 Agent 研报检索链路。"
                "内容覆盖医保谈判、集采政策、放量上涨、放量下跌、缩量上涨和公告事件关联。"
            ),
            "summary_text": f"{MARKER} 合成研报摘要：政策风险与量价异动。",
            "source_type": "synthetic",
            "source_url": "https://synthetic.local/vector/report/600276/risk-price-volume",
            "file_type": "synthetic",
            "original_filename": "synthetic_report_risk_price_volume.txt",
        },
    ]


def seed_synthetic_data() -> dict[str, Any]:
    with SessionLocal() as db:
        _ensure_company(db)

        news_rows = []
        news_created = 0
        for payload in _synthetic_news_rows():
            row, created = _upsert_by_dedup(db, NewsRawHot, "news", payload, "news_uid")
            news_rows.append(row)
            news_created += int(created)

        report_rows = []
        report_created = 0
        for payload in _synthetic_report_rows():
            row, created = _upsert_by_dedup(db, ResearchReportHot, "research_report", payload, "report_uid")
            report_rows.append(row)
            report_created += int(created)

        db.commit()
        news_ids = [row.id for row in news_rows]
        report_ids = [row.id for row in report_rows]

        news_chunks = sync.sync_news_by_ids(db, news_ids, is_hot=True)
        report_chunks = sync.sync_research_reports_by_ids(db, report_ids, is_hot=True)
        db.commit()

    vector_store = get_vector_store()
    return {
        "marker": MARKER,
        "news": {
            "ids": news_ids,
            "created": news_created,
            "synced_chunks": news_chunks,
            "collection_count": vector_store.count(doc_type="news"),
        },
        "report": {
            "ids": report_ids,
            "created": report_created,
            "synced_chunks": report_chunks,
            "collection_count": vector_store.count(doc_type="report"),
        },
    }


def main() -> None:
    print(json.dumps(seed_synthetic_data(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
