from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import inspect, select, text

from app.core.database.session import SessionLocal, engine
from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.utils.dedup import prepare_dedup_record


TABLES = [
    ("financial", FinancialHot, "financial_hot", "ux_financial_dedup_key", "idx_financial_content_hash"),
    ("financial", FinancialArchive, "financial_archive", "ux_financial_archive_dedup_key", "idx_financial_archive_content_hash"),
    ("announcement", AnnouncementHot, "announcement_hot", "ux_announcement_dedup_key", "idx_announcement_content_hash"),
    ("announcement", AnnouncementArchive, "announcement_archive", "ux_announcement_archive_dedup_key", "idx_announcement_archive_content_hash"),
    ("research_report", ResearchReportHot, "research_report_hot", "ux_rr_dedup_key", "idx_rr_content_hash"),
    ("research_report", ResearchReportArchive, "research_report_archive", "ux_rr_archive_dedup_key", "idx_rr_archive_content_hash"),
    ("news", NewsHot, "news_hot", "ux_news_dedup_key", "idx_news_content_hash"),
    ("news", NewsArchive, "news_archive", "ux_news_archive_dedup_key", "idx_news_archive_content_hash"),
]


def _quote_name(name: str) -> str:
    return f"`{name}`"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def ensure_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for _, _, table_name, _, _ in TABLES:
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            if "dedup_key" not in existing:
                conn.execute(text(f"ALTER TABLE {_quote_name(table_name)} ADD COLUMN dedup_key VARCHAR(128) NULL"))
                print(f"[schema] added {table_name}.dedup_key")
            if "content_hash" not in existing:
                conn.execute(text(f"ALTER TABLE {_quote_name(table_name)} ADD COLUMN content_hash VARCHAR(64) NULL"))
                print(f"[schema] added {table_name}.content_hash")


def backfill_rows() -> None:
    with SessionLocal() as db:
        for data_type, model, table_name, _, _ in TABLES:
            rows = list(db.execute(select(model)).scalars().all())
            changed = 0
            for row in rows:
                prepared = prepare_dedup_record(data_type, _row_to_dict(row))
                if row.dedup_key != prepared["dedup_key"]:
                    row.dedup_key = prepared["dedup_key"]
                    changed += 1
                if row.content_hash != prepared["content_hash"]:
                    row.content_hash = prepared["content_hash"]
                    changed += 1
            db.commit()
            print(f"[backfill] {table_name}: rows={len(rows)}, field_updates={changed}")


def duplicate_keys(table_name: str) -> list[dict[str, Any]]:
    sql = text(
        f"""
        SELECT dedup_key, COUNT(*) AS cnt
        FROM {_quote_name(table_name)}
        WHERE dedup_key IS NOT NULL
        GROUP BY dedup_key
        HAVING COUNT(*) > 1
        LIMIT 20
        """
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(sql).mappings().all()]


def ensure_indexes() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for _, _, table_name, unique_index, content_index in TABLES:
            existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
            if content_index not in existing_indexes:
                conn.execute(text(f"CREATE INDEX {content_index} ON {_quote_name(table_name)} (content_hash)"))
                print(f"[index] created {content_index}")

            duplicates = duplicate_keys(table_name)
            if duplicates:
                print(f"[index] skipped {unique_index}: duplicate dedup_key rows exist in {table_name}")
                for item in duplicates[:3]:
                    print(f"        {item['dedup_key']} -> {item['cnt']}")
                continue

            if unique_index not in existing_indexes:
                conn.execute(text(f"CREATE UNIQUE INDEX {unique_index} ON {_quote_name(table_name)} (dedup_key)"))
                print(f"[index] created {unique_index}")


def main() -> None:
    ensure_columns()
    backfill_rows()
    ensure_indexes()
    print("[done] dedup schema migration finished")


if __name__ == "__main__":
    main()
