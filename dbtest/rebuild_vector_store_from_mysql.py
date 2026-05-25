from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.database.session import SessionLocal
from app.knowledge.store import get_store, get_vector_store
from app.knowledge.sync import (
    sync_announcements,
    sync_company_profiles,
    sync_financial_notes,
    sync_news,
    sync_research_reports,
)
from app.paths import CHROMA_DB_DIR, KNOWLEDGE_STORE_FILE


def run_rebuild() -> dict:
    steps: list[tuple[str, object, dict]] = [
        ("announcement_hot", sync_announcements, {"is_hot": True}),
        ("announcement_archive", sync_announcements, {"is_hot": False}),
        ("financial_hot", sync_financial_notes, {"is_hot": True}),
        ("financial_archive", sync_financial_notes, {"is_hot": False}),
        ("news_hot", sync_news, {"is_hot": True}),
        ("news_archive", sync_news, {"is_hot": False}),
        ("research_report_hot", sync_research_reports, {"is_hot": True}),
        ("research_report_archive", sync_research_reports, {"is_hot": False}),
        ("company_profile", sync_company_profiles, {}),
    ]

    step_counts: dict[str, int] = {}
    with SessionLocal() as db:
        try:
            for name, sync_fn, kwargs in steps:
                step_counts[name] = int(sync_fn(db, **kwargs))
            db.commit()
        except Exception:
            db.rollback()
            raise

    vector_store = get_vector_store()
    collection_counts = {
        doc_type: vector_store.count(doc_type=doc_type)
        for doc_type in ["announcement", "financial_note", "news", "report", "company_profile"]
    }

    tfidf_store = get_store()
    return {
        "chroma_path": str(CHROMA_DB_DIR),
        "tfidf_path": str(KNOWLEDGE_STORE_FILE),
        "step_counts": step_counts,
        "collection_counts": collection_counts,
        "tfidf_doc_count": len(tfidf_store.docs),
        "total_backfilled_chunks": sum(step_counts.values()),
    }


def main() -> None:
    result = run_rebuild()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
