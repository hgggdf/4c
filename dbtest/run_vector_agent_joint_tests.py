from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient

from agent.dialogue_agent import DialogueAgent
from agent.integration.tool_executor import execute_tool_plan
from agent.tools import retrieval_tools
from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialNotesHot
from app.core.database.models.news_hot import NewsRawHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.session import SessionLocal
from app.core.utils.dedup import prepare_dedup_record
from app.knowledge import sync
from app.knowledge.store import get_store, get_vector_store
from app.service.container import ServiceContainer
from app.service.requests import SearchRequest
from main import app


MARKER = "[VECTOR_AGENT_TEST]"
STOCK_CODE = "600276"
STOCK_NAME = "恒瑞医药"


def _contains_marker(item: dict) -> bool:
    text = str(item.get("text") or item.get("summary") or "")
    metadata = item.get("metadata") or {}
    source = item.get("source_record") or {}
    return any(
        MARKER in str(value)
        for value in [
            text,
            metadata.get("title"),
            metadata.get("category"),
            metadata.get("source_url"),
            source.get("title"),
            source.get("content"),
            source.get("summary_text"),
            source.get("business_summary"),
            source.get("report_type"),
            source.get("source_url"),
        ]
    ) or metadata.get("category") == "vector_agent_test" or source.get("report_type") == "vector_agent_test"


class VectorAgentJointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_id = uuid4().hex[:12]
        cls.original_company: dict | None = None
        cls.ids: dict[str, int] = {}
        cls.uids: dict[str, str] = {}
        cls.queries = {
            "announcement": "恒瑞医药创新药授权关系库向量库联合测试",
            "news": "恒瑞医药国际化合作新闻 Agent 检索联合测试",
            "financial_note": "88888888.88 23660000.00 12880000.00 财务联合测试",
            "report": "恒瑞医药管线估值研报 Agent 工具执行链路",
            "company_profile": "恒瑞医药公司画像创新药国际化联合测试",
        }
        cls._cleanup_seed_rows()
        cls._seed_rows_and_vectors()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._restore_company_profile()
        cls._cleanup_seed_rows()

    @classmethod
    def _ensure_company(cls, db) -> Company:
        company = db.get(Company, STOCK_CODE)
        if company is None:
            company = Company(
                stock_code=STOCK_CODE,
                stock_name=STOCK_NAME,
                full_name="江苏恒瑞医药股份有限公司",
                exchange="SH",
                industry_level1="医药生物",
            )
            db.add(company)
            db.flush()
        return company

    @classmethod
    def _delete_vectors(cls, doc_type: str, source_table: str, rows: list) -> None:
        if not rows:
            return
        source_pks = [str(row.id) for row in rows if getattr(row, "id", None) is not None]
        source_uids = [str(row.dedup_key) for row in rows if getattr(row, "dedup_key", None)]
        get_vector_store().delete_by_source(
            doc_type=doc_type,
            source_table=source_table,
            source_pks=source_pks,
            source_uids=source_uids,
        )
        get_store().delete_by_source(
            source_table=source_table,
            source_pks=source_pks,
            source_uids=source_uids,
        )

    @classmethod
    def _cleanup_seed_rows(cls) -> None:
        with SessionLocal() as db:
            rows_by_type = [
                (
                    "announcement",
                    AnnouncementRawHot.__tablename__,
                    db.query(AnnouncementRawHot).filter(AnnouncementRawHot.title.like(f"%{MARKER}%")).all(),
                ),
                (
                    "news",
                    NewsRawHot.__tablename__,
                    db.query(NewsRawHot).filter(NewsRawHot.title.like(f"%{MARKER}%")).all(),
                ),
                (
                    "financial_note",
                    FinancialNotesHot.__tablename__,
                    db.query(FinancialNotesHot).filter(FinancialNotesHot.report_type == "vector_agent_test").all(),
                ),
                (
                    "report",
                    ResearchReportHot.__tablename__,
                    db.query(ResearchReportHot).filter(ResearchReportHot.title.like(f"%{MARKER}%")).all(),
                ),
            ]
            for doc_type, table, rows in rows_by_type:
                cls._delete_vectors(doc_type, table, rows)
                for row in rows:
                    db.delete(row)
            db.commit()

    @classmethod
    def _seed_rows_and_vectors(cls) -> None:
        with SessionLocal() as db:
            company = cls._ensure_company(db)
            cls.original_company = {
                "business_summary": company.business_summary,
                "core_products_json": company.core_products_json,
                "main_segments_json": company.main_segments_json,
            }
            company.business_summary = f"{MARKER} {cls.queries['company_profile']} {cls.run_id}"
            company.core_products_json = {"vector_agent_test": cls.run_id}
            company.main_segments_json = {"segment": "joint_test"}

            announcement = AnnouncementRawHot(
                **prepare_dedup_record(
                    "announcement",
                    {
                        "announcement_uid": f"vector-agent-ann-{cls.run_id}",
                        "stock_code": STOCK_CODE,
                        "title": f"{MARKER} {cls.queries['announcement']} {cls.run_id}",
                        "publish_date": date(2026, 5, 25),
                        "announcement_type": "vector_agent_test",
                        "content": f"{cls.queries['announcement']}，用于关系库、向量库和 Agent 联合测试。{MARKER} {cls.run_id}",
                        "summary_text": f"{MARKER} 公告摘要 {cls.run_id}",
                        "source_url": f"https://vector.test/joint/announcement/{cls.run_id}",
                    },
                )
            )
            news = NewsRawHot(
                **prepare_dedup_record(
                    "news",
                    {
                        "news_uid": f"vector-agent-news-{cls.run_id}",
                        "title": f"{MARKER} {cls.queries['news']} {cls.run_id}",
                        "publish_time": datetime(2026, 5, 25, 11, 0, 0),
                        "source_name": "vector_agent_test",
                        "source_url": f"https://vector.test/joint/news/{cls.run_id}",
                        "news_type": "vector_agent_test",
                        "content": f"{cls.queries['news']}，用于验证 Agent 检索新闻证据。{MARKER} {cls.run_id}",
                        "summary_text": f"{MARKER} 新闻摘要 {cls.run_id}",
                        "related_stock_codes_json": [STOCK_CODE],
                        "related_industry_codes_json": ["MED_MANUFACTURING"],
                        "key_fields_json": {"signal_type": "joint_test", "impact_level": "low"},
                    },
                )
            )
            financial = FinancialNotesHot(
                **prepare_dedup_record(
                    "financial",
                    {
                        "stock_code": STOCK_CODE,
                        "report_date": date(2026, 3, 31),
                        "fiscal_year": 2026,
                        "report_type": "vector_agent_test",
                        "revenue": Decimal("88888888.88"),
                        "gross_profit": Decimal("45678901.23"),
                        "gross_margin": Decimal("0.510000"),
                        "rd_expense": Decimal("12880000.00"),
                        "rd_ratio": Decimal("0.145000"),
                        "net_profit": Decimal("23660000.00"),
                        "eps": Decimal("0.3700"),
                        "operating_cashflow": Decimal("34560000.00"),
                        "source_url": f"https://vector.test/joint/financial/{cls.run_id}",
                    },
                )
            )
            report = ResearchReportHot(
                **prepare_dedup_record(
                    "research_report",
                    {
                        "report_uid": f"vector-agent-report-{cls.run_id}",
                        "scope_type": "company",
                        "stock_code": STOCK_CODE,
                        "industry_code": None,
                        "title": f"{MARKER} {cls.queries['report']} {cls.run_id}",
                        "publish_date": date(2026, 5, 25),
                        "report_org": "vector_agent_test",
                        "content": f"{cls.queries['report']}，用于验证研报向量和 Agent 工具执行链路。{MARKER} {cls.run_id}",
                        "summary_text": f"{MARKER} 研报摘要 {cls.run_id}",
                        "source_type": "vector_agent_test",
                        "source_url": f"https://vector.test/joint/report/{cls.run_id}",
                    },
                )
            )

            db.add_all([announcement, news, financial, report])
            db.commit()
            for row in (announcement, news, financial, report):
                db.refresh(row)

            cls.ids = {
                "announcement": announcement.id,
                "news": news.id,
                "financial_note": financial.id,
                "report": report.id,
            }
            cls.uids = {
                "announcement": announcement.dedup_key,
                "news": news.dedup_key,
                "financial_note": financial.dedup_key,
                "report": report.dedup_key,
                "company_profile": f"company:{STOCK_CODE}",
            }

            counts = {
                "announcement": sync.sync_announcements_by_ids(db, [announcement.id], is_hot=True),
                "news": sync.sync_news_by_ids(db, [news.id], is_hot=True),
                "financial_note": sync.sync_financial_notes_by_ids(db, [financial.id], is_hot=True),
                "report": sync.sync_research_reports_by_ids(db, [report.id], is_hot=True),
                "company_profile": sync.sync_company_profiles_by_ids(db, [STOCK_CODE]),
            }
            missing = {name: count for name, count in counts.items() if count <= 0}
            if missing:
                raise AssertionError(f"vector sync failed for: {missing}")

    @classmethod
    def _restore_company_profile(cls) -> None:
        if not cls.original_company:
            return
        with SessionLocal() as db:
            company = db.get(Company, STOCK_CODE)
            if company is None:
                return
            company.business_summary = cls.original_company["business_summary"]
            company.core_products_json = cls.original_company["core_products_json"]
            company.main_segments_json = cls.original_company["main_segments_json"]
            db.commit()
            if company.business_summary or company.core_products_json or company.main_segments_json:
                sync.sync_company_profiles_by_ids(db, [STOCK_CODE])
            else:
                get_vector_store().delete_by_source(
                    doc_type="company_profile",
                    source_table=Company.__tablename__,
                    source_pks=[STOCK_CODE],
                    source_uids=[f"company:{STOCK_CODE}"],
                )

    def _assert_service_hit(self, result, *, doc_type: str) -> None:
        self.assertTrue(result.success, result.message)
        items = (result.data or {}).get("items") or []
        self.assertTrue(items, f"{doc_type} retrieval returned no items")
        matching = [item for item in items if _contains_marker(item)]
        self.assertTrue(matching, f"{doc_type} retrieval did not return the seeded marker")
        self.assertTrue(any(item.get("source_found") for item in matching), f"{doc_type} was not hydrated")
        self.assertTrue(
            any((item.get("metadata") or {}).get("source_uid") for item in matching),
            f"{doc_type} hit did not carry source_uid",
        )

    def test_retrieval_service_reads_vectors_and_hydrates_relational_rows(self) -> None:
        container = ServiceContainer.build_default()
        cases = [
            ("announcement", container.retrieval.search_announcements, self.queries["announcement"], 5),
            ("news", container.retrieval.search_news, self.queries["news"], 5),
            ("financial_note", container.retrieval.search_financial_notes, self.queries["financial_note"], 20),
            ("report", container.retrieval.search_reports, self.queries["report"], 5),
        ]
        for doc_type, handler, query, top_k in cases:
            with self.subTest(doc_type=doc_type):
                result = handler(SearchRequest(query=query, stock_code=STOCK_CODE, top_k=top_k))
                self._assert_service_hit(result, doc_type=doc_type)

        result = container.retrieval.search_text_evidence(
            SearchRequest(
                query=self.queries["company_profile"],
                stock_code=STOCK_CODE,
                doc_types=["company_profile"],
                top_k=3,
            )
        )
        self._assert_service_hit(result, doc_type="company_profile")

    def test_agent_retrieval_tools_use_modified_vector_store(self) -> None:
        doc_hits = retrieval_tools.search_documents(
            self.queries["announcement"],
            stock_code=STOCK_CODE,
            doc_types=["announcement"],
            top_k=3,
        )
        self.assertTrue(any(_contains_marker(item) and item.get("source_found") for item in doc_hits))

        company_hits = retrieval_tools.search_company_evidence(
            self.queries["company_profile"],
            stock_code=STOCK_CODE,
            top_k=5,
        )
        self.assertTrue(any(_contains_marker(item) and item.get("source_found") for item in company_hits))

        news_hits = retrieval_tools.search_news_evidence(
            self.queries["news"],
            stock_code=STOCK_CODE,
            top_k=3,
        )
        self.assertTrue(any(_contains_marker(item) and item.get("source_found") for item in news_hits))

    def test_tool_executor_vector_related_tools_run_on_real_data(self) -> None:
        plan = [
            {
                "tool_name": "research_report_search",
                "input": {"user_question": self.queries["report"], "stock_code": STOCK_CODE},
                "data_source_type": "研报",
                "can_score": False,
                "freshness": "local",
            },
            {
                "tool_name": "industry_knowledge_search",
                "input": {"user_question": self.queries["news"]},
                "data_source_type": "知识库",
                "can_score": False,
                "freshness": "local",
            },
        ]
        results = execute_tool_plan(plan, dry_run=False)
        self.assertEqual(len(results), 2)

        report_result = results[0]
        self.assertTrue(report_result["success"], report_result.get("error"))
        self.assertTrue(any(_contains_marker(item) for item in report_result.get("data") or []))

        knowledge_result = results[1]
        self.assertTrue(knowledge_result["success"], knowledge_result.get("error"))
        self.assertGreater((knowledge_result.get("data") or {}).get("hit_count", 0), 0)

    def test_dialogue_agent_collects_vector_evidence_without_llm_call(self) -> None:
        agent = DialogueAgent()
        evidence = agent._collect_evidence(
            self.queries["announcement"],
            {"stock_code": STOCK_CODE, "stock_name": STOCK_NAME},
        )
        self.assertTrue(evidence)
        self.assertTrue(any(MARKER in str(item.get("summary") or item.get("title") or "") for item in evidence))

    def test_retrieval_api_route_uses_same_vector_and_db_stack(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/retrieval/hybrid",
                json={
                    "query": self.queries["news"],
                    "stock_code": STOCK_CODE,
                    "doc_types": ["news"],
                    "top_k": 3,
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload.get("success"), payload)
        items = ((payload.get("data") or {}).get("items") or [])
        self.assertTrue(any(_contains_marker(item) and item.get("source_found") for item in items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
