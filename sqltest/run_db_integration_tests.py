from __future__ import annotations

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import import_batch
from app.core.database.models.announcement_hot import AnnouncementArchive, AnnouncementHot
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialArchive, FinancialHot
from app.core.database.models.news_hot import NewsArchive, NewsHot
from app.core.database.models.research_report_hot import ResearchReportArchive, ResearchReportHot
from app.core.database.session import SessionLocal
from app.core.repositories.announcement_write_repository import AnnouncementWriteRepository
from app.core.repositories.financial_write_repository import FinancialWriteRepository
from app.core.repositories.news_write_repository import NewsWriteRepository
from app.core.repositories.research_report_write_repository import ResearchReportWriteRepository
from app.core.utils.dedup import build_dedup_key, prepare_dedup_record
from ingest_center import import_worker
from ingest_center.hot_archive_service import HotArchiveService


STOCK_CODE = "600276"
MARK = "[DEDUP_TEST_OPENCLAW]"


def cleanup_test_rows() -> None:
    with SessionLocal() as db:
        for model in (FinancialHot, FinancialArchive):
            db.execute(
                delete(model).where(
                    model.stock_code == STOCK_CODE,
                    model.report_type.like("dedup_test%"),
                )
            )
        for model in (AnnouncementHot, AnnouncementArchive):
            db.execute(delete(model).where(model.title.like(f"{MARK}%")))
        for model in (ResearchReportHot, ResearchReportArchive):
            db.execute(delete(model).where(model.title.like(f"{MARK}%")))
        for model in (NewsHot, NewsArchive):
            db.execute(delete(model).where(model.title.like(f"{MARK}%")))
        db.commit()


def one_by_key(db, model, dedup_key: str):
    return db.execute(select(model).where(model.dedup_key == dedup_key)).scalar_one()


def count_by_key(db, model, dedup_key: str) -> int:
    return db.execute(select(func.count()).select_from(model).where(model.dedup_key == dedup_key)).scalar_one()


def as_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class RealDatabaseDedupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with SessionLocal() as db:
            company = db.get(Company, STOCK_CODE)
            if company is None:
                raise RuntimeError(f"Test requires existing company {STOCK_CODE}")

    def setUp(self) -> None:
        cleanup_test_rows()

    def tearDown(self) -> None:
        cleanup_test_rows()

    def test_repository_paths_write_update_read_without_new_input_fields(self) -> None:
        with SessionLocal() as db:
            fin_repo = FinancialWriteRepository(db)
            ann_repo = AnnouncementWriteRepository(db)
            rr_repo = ResearchReportWriteRepository(db)
            news_repo = NewsWriteRepository(db)

            financial = {
                "stock_code": STOCK_CODE,
                "report_date": "2099-01-01",
                "report_type": "dedup_test_repo",
                "revenue": 100,
                "source_url": "https://example.com/financial",
            }
            self.assertNotIn("dedup_key", financial)
            fin_repo.batch_upsert_financial([financial])
            fin_repo.batch_upsert_financial([{**financial, "revenue": 200, "file_hash": "file-v2"}])

            announcement = {
                "stock_code": STOCK_CODE,
                "publish_date": "2099-01-01",
                "title": f"{MARK} repo announcement",
                "content": "old announcement content",
                "source_url": "https://example.com/announcement",
            }
            ann_repo.batch_upsert_raw_announcements([announcement])
            ann_repo.batch_upsert_raw_announcements([{**announcement, "content": "new announcement content"}])

            research = {
                "scope_type": "company",
                "stock_code": STOCK_CODE,
                "publish_date": "2099-01-01",
                "report_org": "repo-test",
                "title": f"{MARK} repo research",
                "content": "old research content",
            }
            rr_repo.batch_upsert_research_reports([research])
            rr_repo.batch_upsert_research_reports([{**research, "content": "new research content"}])

            news = {
                "title": f"{MARK} repo news",
                "publish_time": "2099-01-01 09:00:00",
                "source_name": "repo-test",
                "source_url": "https://example.com/news/repo?id=1&utm_source=test",
                "content": "old news content",
            }
            news_repo.batch_upsert_news_raw([news])
            news_repo.batch_upsert_news_raw([{**news, "source_url": "https://example.com/news/repo?id=1", "content": "new news content"}])
            db.commit()

            fin_key = build_dedup_key("financial", financial)
            ann_key = build_dedup_key("announcement", announcement)
            rr_key = build_dedup_key("research_report", research)
            news_key = build_dedup_key("news", news)

            self.assertEqual(count_by_key(db, FinancialHot, fin_key), 1)
            self.assertEqual(as_float(one_by_key(db, FinancialHot, fin_key).revenue), 200.0)
            self.assertEqual(count_by_key(db, AnnouncementHot, ann_key), 1)
            self.assertEqual(one_by_key(db, AnnouncementHot, ann_key).content, "new announcement content")
            self.assertEqual(count_by_key(db, ResearchReportHot, rr_key), 1)
            self.assertEqual(one_by_key(db, ResearchReportHot, rr_key).content, "new research content")
            self.assertEqual(count_by_key(db, NewsHot, news_key), 1)
            self.assertEqual(one_by_key(db, NewsHot, news_key).content, "new news content")

    def test_ingest_worker_paths_write_update_read_without_new_input_fields(self) -> None:
        with SessionLocal() as db:
            financial = {
                "stock_code": STOCK_CODE,
                "report_date": "2099-01-02",
                "report_type": "dedup_test_worker",
                "revenue": 300,
            }
            announcement = {
                "stock_code": STOCK_CODE,
                "publish_date": "2099-01-02",
                "title": f"{MARK} worker announcement",
                "content": "old worker announcement",
            }
            research = {
                "scope_type": "company",
                "stock_code": STOCK_CODE,
                "publish_date": "2099-01-02",
                "report_org": "worker-test",
                "title": f"{MARK} worker research",
                "content": "old worker research",
            }
            news = {
                "title": f"{MARK} worker news",
                "publish_time": "2099-01-02 09:00:00",
                "source_name": "worker-test",
                "source_url": "https://example.com/news/worker?id=1",
                "content": "old worker news",
            }

            import_worker._merge_financial(db, [financial, {**financial, "revenue": 400}])
            import_worker._merge_announcement(db, [announcement, {**announcement, "content": "new worker announcement"}])
            import_worker._merge_research_report(db, [research, {**research, "content": "new worker research"}])
            import_worker._merge_news(db, [news, {**news, "content": "new worker news"}])
            db.commit()

            self.assertEqual(count_by_key(db, FinancialHot, build_dedup_key("financial", financial)), 1)
            self.assertEqual(count_by_key(db, AnnouncementHot, build_dedup_key("announcement", announcement)), 1)
            self.assertEqual(count_by_key(db, ResearchReportHot, build_dedup_key("research_report", research)), 1)
            self.assertEqual(count_by_key(db, NewsHot, build_dedup_key("news", news)), 1)

    def test_import_batch_paths_accept_original_openclaw_record_format(self) -> None:
        batch_dir = ROOT / "sqltest" / "_tmp_openclaw_batch"
        batch_dir.mkdir(parents=True, exist_ok=True)

        financial = {
            "stock_code": STOCK_CODE,
            "report_date": "2099-01-03",
            "report_type": "dedup_test_batch",
            "revenue": 500,
        }
        announcement = {
            "stock_code": STOCK_CODE,
            "publish_date": "2099-01-03",
            "title": f"{MARK} batch announcement",
            "content": "old batch announcement",
        }
        research = {
            "scope_type": "company",
            "stock_code": STOCK_CODE,
            "publish_date": "2099-01-03",
            "report_org": "batch-test",
            "title": f"{MARK} batch research",
            "content": "old batch research",
        }
        news = {
            "title": f"{MARK} batch news",
            "publish_time": "2099-01-03 09:00:00",
            "source_name": "batch-test",
            "source_url": "https://example.com/news/batch?id=1",
            "content": "old batch news",
        }

        self.assertEqual(import_batch.ingest_financial("dedup-test", batch_dir, [financial, {**financial, "revenue": 600}])[:2], (2, 0))
        self.assertEqual(import_batch.ingest_announcement("dedup-test", batch_dir, [announcement, {**announcement, "content": "new batch announcement"}])[:2], (2, 0))
        self.assertEqual(import_batch.ingest_research_report("dedup-test", batch_dir, [research, {**research, "content": "new batch research"}])[:2], (2, 0))
        self.assertEqual(import_batch.ingest_news("dedup-test", batch_dir, [news, {**news, "content": "new batch news"}])[:2], (2, 0))

        with SessionLocal() as db:
            self.assertEqual(count_by_key(db, FinancialHot, build_dedup_key("financial", financial)), 1)
            self.assertEqual(count_by_key(db, AnnouncementHot, build_dedup_key("announcement", announcement)), 1)
            self.assertEqual(count_by_key(db, ResearchReportHot, build_dedup_key("research_report", research)), 1)
            self.assertEqual(count_by_key(db, NewsHot, build_dedup_key("news", news)), 1)
            self.assertIsNotNone(one_by_key(db, FinancialHot, build_dedup_key("financial", financial)).content_hash)
            self.assertIsNotNone(one_by_key(db, AnnouncementHot, build_dedup_key("announcement", announcement)).content_hash)

    def test_hot_archive_merge_and_restore_use_dedup_key(self) -> None:
        with SessionLocal() as db:
            financial_payload = {
                "stock_code": STOCK_CODE,
                "report_date": date(2099, 1, 4),
                "report_type": "dedup_test_archive",
                "revenue": 800,
            }
            prepared_fin = prepare_dedup_record("financial", financial_payload)
            archive_fin = FinancialArchive(
                stock_code=STOCK_CODE,
                report_date=financial_payload["report_date"],
                report_type=financial_payload["report_type"],
                fiscal_year=2099,
                revenue=Decimal("700"),
                dedup_key=prepared_fin["dedup_key"],
                content_hash="old-archive-hash",
            )
            hot_fin = FinancialHot(
                stock_code=STOCK_CODE,
                report_date=financial_payload["report_date"],
                report_type=financial_payload["report_type"],
                fiscal_year=2099,
                revenue=Decimal("800"),
                dedup_key=prepared_fin["dedup_key"],
                content_hash=prepared_fin["content_hash"],
            )
            db.add_all([archive_fin, hot_fin])
            db.commit()

            service = HotArchiveService(db)
            moved = service._move_to_archive([hot_fin], FinancialArchive, "financial_hot")
            self.assertEqual(moved, 1)
            self.assertEqual(count_by_key(db, FinancialHot, prepared_fin["dedup_key"]), 0)
            self.assertEqual(count_by_key(db, FinancialArchive, prepared_fin["dedup_key"]), 1)
            self.assertEqual(as_float(one_by_key(db, FinancialArchive, prepared_fin["dedup_key"]).revenue), 800.0)

            announcement_payload = {
                "stock_code": STOCK_CODE,
                "publish_date": date(2099, 1, 4),
                "title": f"{MARK} restore announcement",
                "content": "archive restore content",
            }
            prepared_ann = prepare_dedup_record("announcement", announcement_payload)
            hot_ann = AnnouncementHot(
                announcement_uid="dedup-test-hot-restore",
                stock_code=STOCK_CODE,
                publish_date=announcement_payload["publish_date"],
                title=announcement_payload["title"],
                content="old hot content",
                dedup_key=prepared_ann["dedup_key"],
                content_hash="old-hot-hash",
            )
            archive_ann = AnnouncementArchive(
                announcement_uid="dedup-test-archive-restore",
                stock_code=STOCK_CODE,
                publish_date=announcement_payload["publish_date"],
                title=announcement_payload["title"],
                content=announcement_payload["content"],
                dedup_key=prepared_ann["dedup_key"],
                content_hash=prepared_ann["content_hash"],
            )
            db.add_all([hot_ann, archive_ann])
            db.commit()

            self.assertTrue(service.restore_hot("announcement", archive_ann.id))
            restored = one_by_key(db, AnnouncementHot, prepared_ann["dedup_key"])
            self.assertEqual(restored.content, "archive restore content")
            self.assertEqual(restored.announcement_uid, "dedup-test-hot-restore")


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        cleanup_test_rows()
