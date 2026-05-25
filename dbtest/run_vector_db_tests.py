from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.database.models.announcement_hot import AnnouncementRawArchive, AnnouncementRawHot
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialNotesHot
from app.core.database.models.news_hot import NewsRawArchive, NewsRawHot
from app.core.database.models.vector_and_job import VectorDocumentIndex
from app.core.database.session import SessionLocal
from app.core.utils.dedup import prepare_dedup_record
from app.knowledge import sync
from app.knowledge.store import ACTIVE_COLLECTIONS, _get_collection, get_store, get_vector_store
from app.service.adapters.vector_store import KnowledgeVectorStoreAdapter
from app.service.retrieval_service import RetrievalService


MARKER = "[VECTOR_DB_TEST]"
STOCK_CODE = "600276"


def _collection_payload(doc_type: str, source_uid: str) -> dict:
    collection = _get_collection(ACTIVE_COLLECTIONS[doc_type])
    return collection.get(
        where={"source_uid": source_uid},
        include=["metadatas", "documents"],
    )


def _vector_count(doc_type: str, source_uid: str) -> int:
    return len(_collection_payload(doc_type, source_uid).get("ids") or [])


class VectorDbIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = uuid4().hex[:12]
        self._cleanup_test_rows()

    def tearDown(self) -> None:
        self._cleanup_test_rows()

    def _ensure_company(self, db) -> Company:
        company = db.get(Company, STOCK_CODE)
        if company is None:
            company = Company(
                stock_code=STOCK_CODE,
                stock_name="恒瑞医药",
                full_name="江苏恒瑞医药股份有限公司",
                exchange="SH",
                industry_level1="医药生物",
            )
            db.add(company)
            db.flush()
        return company

    def _delete_vectors(self, doc_type: str, source_table: str, rows: list) -> None:
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

    def _delete_vector_index(self, db, rows: list) -> None:
        source_uids = [str(row.dedup_key) for row in rows if getattr(row, "dedup_key", None)]
        for source_uid in source_uids:
            db.query(VectorDocumentIndex).filter(VectorDocumentIndex.source_uid == source_uid).delete(
                synchronize_session=False
            )

    def _index_rows(self, db, source_uid: str) -> list[VectorDocumentIndex]:
        return db.query(VectorDocumentIndex).filter(VectorDocumentIndex.source_uid == source_uid).all()

    def _cleanup_test_rows(self) -> None:
        with SessionLocal() as db:
            ann_hot = db.query(AnnouncementRawHot).filter(AnnouncementRawHot.title.like(f"%{MARKER}%")).all()
            ann_archive = db.query(AnnouncementRawArchive).filter(AnnouncementRawArchive.title.like(f"%{MARKER}%")).all()
            news_hot = db.query(NewsRawHot).filter(NewsRawHot.title.like(f"%{MARKER}%")).all()
            news_archive = db.query(NewsRawArchive).filter(NewsRawArchive.title.like(f"%{MARKER}%")).all()
            financial_rows = db.query(FinancialNotesHot).filter(FinancialNotesHot.report_type == "vector_db_test").all()

            self._delete_vectors("announcement", AnnouncementRawHot.__tablename__, ann_hot)
            self._delete_vectors("announcement", AnnouncementRawArchive.__tablename__, ann_archive)
            self._delete_vectors("news", NewsRawHot.__tablename__, news_hot)
            self._delete_vectors("news", NewsRawArchive.__tablename__, news_archive)
            self._delete_vectors("financial_note", FinancialNotesHot.__tablename__, financial_rows)
            self._delete_vector_index(db, ann_hot + ann_archive + news_hot + news_archive + financial_rows)
            db.query(VectorDocumentIndex).filter(VectorDocumentIndex.chunk_text.like(f"%{MARKER}%")).delete(
                synchronize_session=False
            )

            for row in ann_hot + ann_archive + news_hot + news_archive + financial_rows:
                db.delete(row)
            db.commit()

    def _assert_source_uid_vectors(
        self,
        *,
        doc_type: str,
        source_uid: str,
        source_table: str,
        is_hot: int | None = None,
    ) -> list[dict]:
        payload = _collection_payload(doc_type, source_uid)
        ids = payload.get("ids") or []
        self.assertGreater(len(ids), 0, f"{doc_type} did not create vector chunks for {source_uid}")

        metadatas = payload.get("metadatas") or []
        self.assertTrue(metadatas, "vector chunks should include metadata")
        self.assertTrue(all(meta.get("source_uid") == source_uid for meta in metadatas))
        self.assertTrue(all(meta.get("source_table") == source_table for meta in metadatas))
        if is_hot is not None:
            self.assertTrue(all(int(meta.get("is_hot")) == is_hot for meta in metadatas))
        return metadatas

    def test_sync_delete_hydrate_announcement_with_source_uid(self) -> None:
        with SessionLocal() as db:
            self._ensure_company(db)
            payload = prepare_dedup_record(
                "announcement",
                {
                    "announcement_uid": f"vector-ann-{self.run_id}",
                    "stock_code": STOCK_CODE,
                    "title": f"{MARKER} 公告向量测试 {self.run_id}",
                    "publish_date": date(2026, 5, 25),
                    "announcement_type": "vector_db_test",
                    "content": f"{MARKER} 公告内容 {self.run_id} 创新药合作测试文本",
                    "summary_text": f"{MARKER} 公告摘要 {self.run_id}",
                    "source_url": f"https://vector.test/announcement/{self.run_id}",
                },
            )
            row = AnnouncementRawHot(**payload)
            db.add(row)
            db.commit()
            db.refresh(row)

            chunk_count = sync.sync_announcements_by_ids(db, [row.id], is_hot=True)
            self.assertGreater(chunk_count, 0)

            self._assert_source_uid_vectors(
                doc_type="announcement",
                source_uid=row.dedup_key,
                source_table=AnnouncementRawHot.__tablename__,
                is_hot=1,
            )
            index_rows = self._index_rows(db, row.dedup_key)
            self.assertEqual(len(index_rows), chunk_count)
            self.assertTrue(all(item.vector_status == "success" for item in index_rows))
            self.assertTrue(all(item.vector_collection == ACTIVE_COLLECTIONS["announcement"] for item in index_rows))
            self.assertTrue(all(item.vector_id for item in index_rows))
            self.assertEqual(row.vector_status, "success")
            db.commit()

            service = RetrievalService(ctx=SimpleNamespace())
            record = service._load_source_record(
                db,
                doc_type="announcement",
                source_pk=str(row.id),
                source_table=AnnouncementRawHot.__tablename__,
                source_uid=row.dedup_key,
            )
            self.assertIsNotNone(record)
            self.assertEqual(record["id"], row.id)

            deleted = KnowledgeVectorStoreAdapter().delete_by_source(
                doc_type="announcement",
                source_table=AnnouncementRawHot.__tablename__,
                source_pks=[row.id],
                source_uids=[row.dedup_key],
            )
            self.assertGreater(deleted, 0)
            self.assertEqual(_vector_count("announcement", row.dedup_key), 0)
            db.commit()
            self.assertEqual(len(self._index_rows(db, row.dedup_key)), 0)

    def test_hot_to_archive_resync_replaces_hot_vector(self) -> None:
        with SessionLocal() as db:
            self._ensure_company(db)
            payload = prepare_dedup_record(
                "news",
                {
                    "news_uid": f"vector-news-{self.run_id}",
                    "title": f"{MARKER} 新闻冷热库测试 {self.run_id}",
                    "publish_time": datetime(2026, 5, 25, 10, 0, 0),
                    "source_name": "vector_db_test",
                    "source_url": f"https://vector.test/news/{self.run_id}",
                    "news_type": "vector_db_test",
                    "content": f"{MARKER} 新闻内容 {self.run_id} 热库转冷库向量替换",
                    "summary_text": f"{MARKER} 新闻摘要 {self.run_id}",
                    "related_stock_codes_json": [STOCK_CODE],
                    "related_industry_codes_json": ["MED_MANUFACTURING"],
                    "key_fields_json": {"signal_type": "test", "impact_level": "low"},
                },
            )
            hot_row = NewsRawHot(**payload)
            db.add(hot_row)
            db.commit()
            db.refresh(hot_row)

            hot_chunks = sync.sync_news_by_ids(db, [hot_row.id], is_hot=True)
            self.assertGreater(hot_chunks, 0)
            self._assert_source_uid_vectors(
                doc_type="news",
                source_uid=hot_row.dedup_key,
                source_table=NewsRawHot.__tablename__,
                is_hot=1,
            )
            self.assertEqual(len(self._index_rows(db, hot_row.dedup_key)), hot_chunks)
            self.assertEqual(hot_row.vector_status, "success")

            archive_payload = {
                key: getattr(hot_row, key)
                for key in [
                    "news_uid",
                    "title",
                    "publish_time",
                    "source_name",
                    "source_url",
                    "news_type",
                    "content",
                    "summary_text",
                    "related_stock_codes_json",
                    "related_industry_codes_json",
                    "key_fields_json",
                    "file_path",
                    "file_type",
                    "original_filename",
                    "file_hash",
                    "dedup_key",
                    "content_hash",
                    "vector_status",
                    "query_count",
                ]
            }
            archive_row = NewsRawArchive(**archive_payload)
            db.add(archive_row)
            db.delete(hot_row)
            db.commit()
            db.refresh(archive_row)

            cold_chunks = sync.sync_news_by_ids(db, [archive_row.id], is_hot=False)
            self.assertGreater(cold_chunks, 0)
            metadatas = self._assert_source_uid_vectors(
                doc_type="news",
                source_uid=archive_row.dedup_key,
                source_table=NewsRawArchive.__tablename__,
                is_hot=0,
            )
            self.assertFalse(any(meta.get("source_table") == NewsRawHot.__tablename__ for meta in metadatas))
            index_rows = self._index_rows(db, archive_row.dedup_key)
            self.assertEqual(len(index_rows), cold_chunks)
            self.assertTrue(all(item.source_table == NewsRawArchive.__tablename__ for item in index_rows))
            self.assertEqual(archive_row.vector_status, "success")

            service = RetrievalService(ctx=SimpleNamespace())
            record = service._load_source_record(
                db,
                doc_type="news",
                source_pk=str(archive_row.id),
                source_table=NewsRawArchive.__tablename__,
                source_uid=archive_row.dedup_key,
            )
            self.assertIsNotNone(record)
            self.assertEqual(record["id"], archive_row.id)

    def test_financial_note_sync_uses_current_financial_fields(self) -> None:
        with SessionLocal() as db:
            self._ensure_company(db)
            payload = prepare_dedup_record(
                "financial",
                {
                    "stock_code": STOCK_CODE,
                    "report_date": date(2026, 3, 31),
                    "fiscal_year": 2026,
                    "report_type": "vector_db_test",
                    "revenue": Decimal("123456789.12"),
                    "gross_profit": Decimal("56789012.34"),
                    "gross_margin": Decimal("0.460000"),
                    "rd_expense": Decimal("12340000.00"),
                    "rd_ratio": Decimal("0.100000"),
                    "net_profit": Decimal("23450000.00"),
                    "eps": Decimal("0.3600"),
                    "operating_cashflow": Decimal("34560000.00"),
                    "source_url": f"https://vector.test/financial/{self.run_id}",
                },
            )
            row = FinancialNotesHot(**payload)
            db.add(row)
            db.commit()
            db.refresh(row)

            chunk_count = sync.sync_financial_notes_by_ids(db, [row.id], is_hot=True)
            self.assertGreater(chunk_count, 0)
            metadatas = self._assert_source_uid_vectors(
                doc_type="financial_note",
                source_uid=row.dedup_key,
                source_table=FinancialNotesHot.__tablename__,
                is_hot=1,
            )
            self.assertTrue(all(meta.get("category") == "vector_db_test" for meta in metadatas))
            index_rows = self._index_rows(db, row.dedup_key)
            self.assertEqual(len(index_rows), chunk_count)
            self.assertTrue(all(item.doc_type == "financial_note" for item in index_rows))

            service = RetrievalService(ctx=SimpleNamespace())
            record = service._load_source_record(
                db,
                doc_type="financial_note",
                source_pk=str(row.id),
                source_table=FinancialNotesHot.__tablename__,
                source_uid=row.dedup_key,
            )
            self.assertIsNotNone(record)
            self.assertEqual(record["id"], row.id)

    def test_company_profile_sync_and_hydration_uses_stock_code(self) -> None:
        source_uid = f"company:{STOCK_CODE}"
        with SessionLocal() as db:
            company = self._ensure_company(db)
            original = {
                "business_summary": company.business_summary,
                "core_products_json": company.core_products_json,
                "main_segments_json": company.main_segments_json,
            }
            try:
                company.business_summary = f"{MARKER} 公司画像向量测试 {self.run_id} 创新药国际化"
                company.core_products_json = {"vector_db_test": self.run_id}
                company.main_segments_json = {"segment": "test"}
                db.commit()

                chunk_count = sync.sync_company_profiles_by_ids(db, [STOCK_CODE])
                self.assertGreater(chunk_count, 0)
                self._assert_source_uid_vectors(
                    doc_type="company_profile",
                    source_uid=source_uid,
                    source_table=Company.__tablename__,
                    is_hot=1,
                )
                index_rows = self._index_rows(db, source_uid)
                self.assertEqual(len(index_rows), chunk_count)
                self.assertTrue(all(item.source_table == Company.__tablename__ for item in index_rows))

                service = RetrievalService(ctx=SimpleNamespace())
                record = service._load_source_record(
                    db,
                    doc_type="company_profile",
                    source_pk=STOCK_CODE,
                    source_table=Company.__tablename__,
                    source_uid=source_uid,
                )
                self.assertIsNotNone(record)
                self.assertEqual(record["stock_code"], STOCK_CODE)
            finally:
                company = db.get(Company, STOCK_CODE)
                if company is not None:
                    company.business_summary = original["business_summary"]
                    company.core_products_json = original["core_products_json"]
                    company.main_segments_json = original["main_segments_json"]
                    db.commit()
                    if company.business_summary or company.core_products_json or company.main_segments_json:
                        sync.sync_company_profiles_by_ids(db, [STOCK_CODE])
                        db.commit()
                    else:
                        get_vector_store().delete_by_source(
                            doc_type="company_profile",
                            source_table=Company.__tablename__,
                            source_pks=[STOCK_CODE],
                            source_uids=[source_uid],
                        )
                        sync.delete_vector_index_entries(
                            db,
                            source_table=Company.__tablename__,
                            source_pks=[STOCK_CODE],
                            source_uids=[source_uid],
                        )
                        db.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
