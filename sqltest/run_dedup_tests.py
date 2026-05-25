from __future__ import annotations

import inspect
import py_compile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

MODIFIED_FILES = [
    "backend/app/core/utils/dedup.py",
    "backend/app/core/database/models/financial_hot.py",
    "backend/app/core/database/models/announcement_hot.py",
    "backend/app/core/database/models/research_report_hot.py",
    "backend/app/core/database/models/news_hot.py",
    "backend/app/core/repositories/base.py",
    "backend/app/core/repositories/financial_write_repository.py",
    "backend/app/core/repositories/announcement_write_repository.py",
    "backend/app/core/repositories/research_report_write_repository.py",
    "backend/app/core/repositories/news_write_repository.py",
    "backend/ingest_center/import_worker.py",
    "backend/ingest_center/hot_archive_service.py",
    "backend/import_batch.py",
    "sqltest/migrate_dedup_columns.py",
]


class CompileTests(unittest.TestCase):
    def test_modified_files_compile(self) -> None:
        for rel_path in MODIFIED_FILES:
            with self.subTest(rel_path=rel_path):
                py_compile.compile(str(ROOT / rel_path), doraise=True)


class DedupUtilityTests(unittest.TestCase):
    def test_announcement_key_normalizes_title_prefix(self) -> None:
        from app.core.utils.dedup import build_dedup_key

        first = build_dedup_key(
            "announcement",
            {"stock_code": "600276", "publish_date": "2026-05-20", "title": "600276: 恒瑞医药 获得批准"},
        )
        second = build_dedup_key(
            "announcement",
            {"stock_code": "600276", "publish_date": "2026-05-20", "title": "恒瑞医药   获得批准"},
        )
        self.assertEqual(first, second)

    def test_news_key_prefers_normalized_url(self) -> None:
        from app.core.utils.dedup import build_dedup_key

        first = build_dedup_key(
            "news",
            {"title": "A", "publish_time": "2026-05-20", "source_url": "HTTPS://Example.com/a/?utm_source=x&id=1"},
        )
        second = build_dedup_key(
            "news",
            {"title": "B", "publish_time": "2026-05-21", "source_url": "https://example.com/a?id=1"},
        )
        self.assertEqual(first, second)

    def test_content_hash_ignores_file_path(self) -> None:
        from app.core.utils.dedup import build_content_hash

        first = build_content_hash("news", {"title": "A", "content": "same", "file_path": "one.html"})
        second = build_content_hash("news", {"title": "A", "content": "same", "file_path": "two.html"})
        third = build_content_hash("news", {"title": "A", "content": "changed", "file_path": "two.html"})
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)


class ModelColumnTests(unittest.TestCase):
    def test_hot_and_archive_models_have_dedup_columns(self) -> None:
        from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
        from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
        from app.core.database.models.news_hot import NewsHot, NewsArchive
        from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive

        for model in [
            FinancialHot,
            FinancialArchive,
            AnnouncementHot,
            AnnouncementArchive,
            ResearchReportHot,
            ResearchReportArchive,
            NewsHot,
            NewsArchive,
        ]:
            with self.subTest(model=model.__name__):
                columns = model.__table__.columns
                self.assertIn("dedup_key", columns)
                self.assertIn("content_hash", columns)


class CaptureFinancialRepository:
    from app.core.repositories.financial_write_repository import FinancialWriteRepository

    class Repo(FinancialWriteRepository):
        def __init__(self) -> None:
            super().__init__(db=None)
            self.calls = []

        def bulk_upsert(self, model, *, items, unique_keys, mutable_fields=None, preserve_on_update=None):
            self.calls.append(
                {
                    "model": model,
                    "items": items,
                    "unique_keys": list(unique_keys),
                    "preserve_on_update": list(preserve_on_update or []),
                }
            )
            return [], 0, 0


class CaptureAnnouncementRepository:
    from app.core.repositories.announcement_write_repository import AnnouncementWriteRepository

    class Repo(AnnouncementWriteRepository):
        def __init__(self) -> None:
            super().__init__(db=None)
            self.calls = []

        def bulk_upsert(self, model, *, items, unique_keys, mutable_fields=None, preserve_on_update=None):
            self.calls.append(
                {
                    "model": model,
                    "items": items,
                    "unique_keys": list(unique_keys),
                    "preserve_on_update": list(preserve_on_update or []),
                }
            )
            return [], 0, 0


class CaptureResearchRepository:
    from app.core.repositories.research_report_write_repository import ResearchReportWriteRepository

    class Repo(ResearchReportWriteRepository):
        def __init__(self) -> None:
            super().__init__(db=None)
            self.calls = []

        def bulk_upsert(self, model, *, items, unique_keys, mutable_fields=None, preserve_on_update=None):
            self.calls.append(
                {
                    "model": model,
                    "items": items,
                    "unique_keys": list(unique_keys),
                    "preserve_on_update": list(preserve_on_update or []),
                }
            )
            return [], 0, 0


class CaptureNewsRepository:
    from app.core.repositories.news_write_repository import NewsWriteRepository

    class Repo(NewsWriteRepository):
        def __init__(self) -> None:
            super().__init__(db=None)
            self.calls = []

        def bulk_upsert(self, model, *, items, unique_keys, mutable_fields=None, preserve_on_update=None):
            self.calls.append(
                {
                    "model": model,
                    "items": items,
                    "unique_keys": list(unique_keys),
                    "preserve_on_update": list(preserve_on_update or []),
                }
            )
            return [], 0, 0


class RepositoryCompatibilityTests(unittest.TestCase):
    def test_base_repository_keeps_backward_compatible_signature(self) -> None:
        from app.core.repositories.base import BaseRepository

        params = inspect.signature(BaseRepository.bulk_upsert).parameters
        self.assertIn("unique_keys", params)
        self.assertIn("preserve_on_update", params)

    def test_financial_repository_uses_dedup_key(self) -> None:
        repo = CaptureFinancialRepository.Repo()
        repo.batch_upsert_financial([{"stock_code": "600276", "report_date": "2026-05-22", "report_type": "daily"}])
        call = repo.calls[-1]
        self.assertEqual(call["unique_keys"], ["dedup_key"])
        self.assertIn("dedup_key", call["items"][0])
        self.assertIn("content_hash", call["items"][0])

    def test_announcement_repository_uses_dedup_key_and_preserves_uid(self) -> None:
        repo = CaptureAnnouncementRepository.Repo()
        repo.batch_upsert_raw_announcements(
            [{"stock_code": "600276", "publish_date": "2026-05-20", "title": "恒瑞医药公告"}]
        )
        call = repo.calls[-1]
        self.assertEqual(call["unique_keys"], ["dedup_key"])
        self.assertIn("announcement_uid", call["preserve_on_update"])
        self.assertIn("dedup_key", call["items"][0])

    def test_research_repository_uses_dedup_key_and_preserves_uid(self) -> None:
        repo = CaptureResearchRepository.Repo()
        repo.batch_upsert_research_reports(
            [{"scope_type": "company", "stock_code": "600276", "publish_date": "2026-05-20", "title": "恒瑞研报"}]
        )
        call = repo.calls[-1]
        self.assertEqual(call["unique_keys"], ["dedup_key"])
        self.assertIn("report_uid", call["preserve_on_update"])
        self.assertIn("dedup_key", call["items"][0])

    def test_news_repository_uses_dedup_key_and_preserves_uid(self) -> None:
        repo = CaptureNewsRepository.Repo()
        repo.batch_upsert_news_raw(
            [{"title": "恒瑞新闻", "publish_time": "2026-05-20 10:00:00", "source_name": "demo"}]
        )
        call = repo.calls[-1]
        self.assertEqual(call["unique_keys"], ["dedup_key"])
        self.assertIn("news_uid", call["preserve_on_update"])
        self.assertIn("dedup_key", call["items"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
