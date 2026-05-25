"""
hot_archive_service.py
======================
冷热库交替服务。

程序内调用接口：
    from ingest_center.hot_archive_service import HotArchiveService
    svc = HotArchiveService(db)

    # 热转冷（定时任务调用）
    svc.archive_cold(dry_run=False)

    # 冷转热（查询命中后调用）
    svc.restore_hot("announcement", source_id=123)

    # query_count 衰减（每30天调用一次）
    svc.decay_query_counts()

转冷规则（v3）：
    财务/公告/研报：report_date/publish_date 超过 2 年，且 query_count < 10
    新闻：publish_time 超过 1 年，且 query_count < 10

回温规则：
    archive 表中 query_count >= 30 → 复制回 hot 表

衰减规则：
    query_count = floor(query_count * 0.5)，每 30 天执行一次
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.database.models.vector_and_job import DataJobLog

logger = logging.getLogger(__name__)

# 热转冷阈值
FINANCIAL_COLD_YEARS = 2
ANNOUNCEMENT_COLD_YEARS = 2
RESEARCH_REPORT_COLD_YEARS = 2
NEWS_COLD_DAYS = 365
COLD_QUERY_THRESHOLD = 10
FINANCIAL_DAILY_COLD_DAYS = 180

# 冷转热阈值
RESTORE_QUERY_THRESHOLD = 30

# 每次处理批量大小
CHUNK_SIZE = 500

ARCHIVE_LEGACY_KEYS = {
    "financial_hot": ["stock_code", "report_date", "report_type"],
    "announcement_hot": ["stock_code", "title", "publish_date"],
    "research_report_hot": ["report_uid"],
    "news_hot": ["news_uid"],
}

RESTORE_LEGACY_KEYS = {
    "financial": ["stock_code", "report_date", "report_type"],
    "announcement": ["stock_code", "title", "publish_date"],
    "research_report": ["report_uid"],
    "news": ["news_uid"],
}

PRESERVE_IDENTITY_FIELDS = {"announcement_uid", "report_uid", "news_uid", "created_at"}


class HotArchiveService:
    """冷热库交替服务，提供热转冷、冷转热、query_count 衰减三个接口。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 热转冷
    # ------------------------------------------------------------------

    def archive_cold(self, dry_run: bool = False) -> dict:
        """
        扫描热库，将超期且低频数据迁移到冷库。

        Args:
            dry_run: True 时只统计不实际迁移

        Returns:
            {"financial": n, "announcement": n, "research_report": n, "news": n}
        """
        result = {}
        result["financial"] = self._archive_financial(dry_run)
        result["announcement"] = self._archive_announcement(dry_run)
        result["research_report"] = self._archive_research_report(dry_run)
        result["news"] = self._archive_news(dry_run)

        if not dry_run:
            self._log_job("archive_cold", "multiple", sum(result.values()), 0)

        logger.info("archive_cold result: %s (dry_run=%s)", result, dry_run)
        return result

    def _archive_financial(self, dry_run: bool) -> int:
        cutoff_normal = date.today() - timedelta(days=FINANCIAL_COLD_YEARS * 365)
        cutoff_daily = date.today() - timedelta(days=FINANCIAL_DAILY_COLD_DAYS)

        # 非 daily：原逻辑（超期 + 低频）
        stmt_normal = (select(FinancialHot)
                       .where(FinancialHot.report_type != 'daily')
                       .where(FinancialHot.report_date < cutoff_normal)
                       .where(FinancialHot.query_count < COLD_QUERY_THRESHOLD))
        # daily：只按时间（半年），不看 query_count
        stmt_daily = (select(FinancialHot)
                      .where(FinancialHot.report_type == 'daily')
                      .where(FinancialHot.report_date < cutoff_daily))

        rows = (list(self.db.execute(stmt_normal).scalars().all()) +
                list(self.db.execute(stmt_daily).scalars().all()))
        if dry_run:
            return len(rows)
        return self._move_to_archive(rows, FinancialArchive, "financial_hot")

    def _archive_announcement(self, dry_run: bool) -> int:
        cutoff = date.today() - timedelta(days=ANNOUNCEMENT_COLD_YEARS * 365)
        stmt = (select(AnnouncementHot)
                .where(AnnouncementHot.publish_date < cutoff)
                .where(AnnouncementHot.query_count < COLD_QUERY_THRESHOLD))
        rows = list(self.db.execute(stmt).scalars().all())
        if dry_run:
            return len(rows)
        return self._move_to_archive(rows, AnnouncementArchive, "announcement_hot")

    def _archive_research_report(self, dry_run: bool) -> int:
        cutoff = date.today() - timedelta(days=RESEARCH_REPORT_COLD_YEARS * 365)
        stmt = (select(ResearchReportHot)
                .where(ResearchReportHot.publish_date < cutoff)
                .where(ResearchReportHot.query_count < COLD_QUERY_THRESHOLD))
        rows = list(self.db.execute(stmt).scalars().all())
        if dry_run:
            return len(rows)
        return self._move_to_archive(rows, ResearchReportArchive, "research_report_hot")

    def _archive_news(self, dry_run: bool) -> int:
        cutoff = datetime.now() - timedelta(days=NEWS_COLD_DAYS)
        stmt = (select(NewsHot)
                .where(NewsHot.publish_time < cutoff)
                .where(NewsHot.query_count < COLD_QUERY_THRESHOLD))
        rows = list(self.db.execute(stmt).scalars().all())
        if dry_run:
            return len(rows)
        return self._move_to_archive(rows, NewsArchive, "news_hot")

    def _move_to_archive(self, rows: list, archive_model, source_table: str) -> int:
        """将热库记录复制到冷库，校验成功后删除热库记录。"""
        moved = 0
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i:i + CHUNK_SIZE]
            for row in chunk:
                try:
                    existing = self._find_existing_archive(row, archive_model, source_table)
                    if existing is None:
                        archive_row = self._copy_to_archive(row, archive_model)
                        self.db.add(archive_row)
                    else:
                        self._merge_common_fields(existing, row)
                    self.db.flush()
                    self.db.delete(row)
                    self.db.flush()
                    moved += 1
                except Exception as exc:
                    logger.warning("archive failed for id=%s: %s", getattr(row, "id", "?"), exc)
                    self.db.rollback()
            self.db.commit()
        return moved

    def _copy_to_archive(self, row: Any, archive_model) -> Any:
        """将热库 ORM 对象的字段复制到冷库模型实例。"""
        archive_cols = {c.name for c in archive_model.__table__.columns if c.name != "id"}
        hot_cols = {c.name for c in row.__table__.columns if c.name != "id"}
        common = archive_cols & hot_cols
        kwargs = {col: getattr(row, col) for col in common}
        return archive_model(**kwargs)

    def _find_existing_archive(self, row: Any, archive_model, source_table: str) -> Any | None:
        legacy_keys = ARCHIVE_LEGACY_KEYS.get(source_table, [])
        return self._find_existing_by_dedup_or_legacy(archive_model, row, legacy_keys)

    def _find_existing_by_dedup_or_legacy(self, model, row: Any, legacy_keys: list[str]) -> Any | None:
        dedup_key = getattr(row, "dedup_key", None)
        if dedup_key:
            existing = self.db.execute(select(model).where(model.dedup_key == dedup_key)).scalar_one_or_none()
            if existing is not None:
                return existing

        if not legacy_keys:
            return None
        stmt = select(model)
        for key in legacy_keys:
            stmt = stmt.where(getattr(model, key) == getattr(row, key))
        return self.db.execute(stmt).scalar_one_or_none()

    def _merge_common_fields(self, target: Any, source: Any) -> None:
        target_cols = {c.name for c in target.__table__.columns if c.name != "id"}
        source_cols = {c.name for c in source.__table__.columns if c.name != "id"}
        for col in target_cols & source_cols:
            if col in PRESERVE_IDENTITY_FIELDS:
                continue
            source_value = getattr(source, col)
            if source_value is None:
                continue
            if col == "query_count":
                target.query_count = max(target.query_count or 0, source_value or 0)
            else:
                setattr(target, col, source_value)

    # ------------------------------------------------------------------
    # 冷转热（回温）
    # ------------------------------------------------------------------

    def restore_hot(self, data_type: str, source_id: int) -> bool:
        """
        将冷库中指定记录复制回热库。

        Args:
            data_type: "financial" | "announcement" | "research_report" | "news"
            source_id: 冷库记录 id

        Returns:
            True 表示成功回温
        """
        mapping = {
            "financial": (FinancialArchive, FinancialHot, RESTORE_LEGACY_KEYS["financial"]),
            "announcement": (AnnouncementArchive, AnnouncementHot, RESTORE_LEGACY_KEYS["announcement"]),
            "research_report": (ResearchReportArchive, ResearchReportHot, RESTORE_LEGACY_KEYS["research_report"]),
            "news": (NewsArchive, NewsHot, RESTORE_LEGACY_KEYS["news"]),
        }
        if data_type not in mapping:
            logger.warning("unknown data_type for restore: %s", data_type)
            return False

        archive_model, hot_model, unique_keys = mapping[data_type]

        archive_row = self.db.get(archive_model, source_id)
        if archive_row is None:
            return False

        # 检查热库是否已存在
        existing = self._find_existing_by_dedup_or_legacy(hot_model, archive_row, unique_keys)

        if existing is None:
            hot_cols = {c.name for c in hot_model.__table__.columns if c.name != "id"}
            archive_cols = {c.name for c in archive_model.__table__.columns if c.name != "id"}
            common = hot_cols & archive_cols
            kwargs = {col: getattr(archive_row, col) for col in common}
            self.db.add(hot_model(**kwargs))
            self.db.commit()
        else:
            self._merge_common_fields(existing, archive_row)
            self.db.commit()

        self._log_job("restore_hot", f"{data_type}_hot", 1, 0)
        return True

    # ------------------------------------------------------------------
    # 查询命中时增加 query_count（供 repository/service 调用）
    # ------------------------------------------------------------------

    def increment_query_count(self, data_type: str, record_id: int, *, is_archive: bool = False) -> None:
        """
        查询命中时 +1 query_count，并在 archive 表中检查是否需要回温。

        Args:
            data_type: "financial" | "announcement" | "research_report" | "news"
            record_id: 记录 id
            is_archive: 是否是冷库记录
        """
        model_map = {
            "financial": (FinancialHot, FinancialArchive),
            "announcement": (AnnouncementHot, AnnouncementArchive),
            "research_report": (ResearchReportHot, ResearchReportArchive),
            "news": (NewsHot, NewsArchive),
        }
        if data_type not in model_map:
            return

        hot_model, archive_model = model_map[data_type]
        model = archive_model if is_archive else hot_model

        row = self.db.get(model, record_id)
        if row is None:
            return

        row.query_count = (row.query_count or 0) + 1
        self.db.commit()

        # 冷库记录达到回温阈值时自动回温（daily 类型不回温）
        if is_archive and row.query_count >= RESTORE_QUERY_THRESHOLD:
            is_daily = data_type == "financial" and getattr(row, "report_type", None) == "daily"
            if not is_daily:
                self.restore_hot(data_type, record_id)

    # ------------------------------------------------------------------
    # query_count 衰减
    # ------------------------------------------------------------------

    def decay_query_counts(self) -> dict:
        """
        对所有热库和冷库表执行 query_count 衰减：floor(query_count * 0.5)。
        每 30 天调用一次。

        Returns:
            各表受影响行数
        """
        tables = [
            FinancialHot, AnnouncementHot, ResearchReportHot, NewsHot,
            FinancialArchive, AnnouncementArchive, ResearchReportArchive, NewsArchive,
        ]
        result = {}
        for model in tables:
            try:
                # 只衰减 query_count > 0 的记录
                stmt = (update(model)
                        .where(model.query_count > 0)
                        .values(query_count=model.query_count * 0 + (model.query_count / 2).cast(int) if False else None))
                # SQLAlchemy 不支持 floor 直接，用原生 SQL
                from sqlalchemy import text as _text
                table_name = model.__tablename__
                r = self.db.execute(
                    _text(f"UPDATE {table_name} SET query_count = FLOOR(query_count * 0.5) WHERE query_count > 0")
                )
                self.db.commit()
                result[table_name] = r.rowcount
            except Exception as exc:
                logger.warning("decay failed for %s: %s", model.__tablename__, exc)
                self.db.rollback()
                result[model.__tablename__] = -1

        self._log_job("decay_query_counts", "multiple", sum(v for v in result.values() if v >= 0), 0)
        return result

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _log_job(self, job_type: str, target_table: str, success: int, failed: int) -> None:
        job = DataJobLog(
            job_type=job_type,
            target_table=target_table,
            job_status="success",
            success_count=success,
            failed_count=failed,
            started_at=datetime.now(),
            finished_at=datetime.now(),
        )
        self.db.add(job)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
