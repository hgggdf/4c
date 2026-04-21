from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from app.core.database.session import SessionLocal
from app.knowledge.store import get_vector_store
from app.knowledge.sync import (
    sync_announcements,
    sync_company_profiles,
    sync_financial_notes,
    sync_news,
)
from app.paths import CHROMA_DB_DIR

BACKFILL_ORDER = (
    ("company_profile", sync_company_profiles),
    ("announcement", sync_announcements),
    ("financial_note", sync_financial_notes),
    ("news", sync_news),
)


def run_backfill() -> dict:
    step_counts: dict[str, int] = {}

    with SessionLocal() as db:
        try:
            for doc_type, sync_fn in BACKFILL_ORDER:
                step_counts[doc_type] = int(sync_fn(db, is_hot=True) if doc_type != "company_profile" else sync_fn(db))
            db.commit()
        except Exception:
            db.rollback()
            raise

    vector_store = get_vector_store()
    collection_counts = {
        doc_type: vector_store.count(doc_type=doc_type)
        for doc_type, _ in BACKFILL_ORDER
    }

    return {
        "chroma_path": str(CHROMA_DB_DIR),
        "step_counts": step_counts,
        "collection_counts": collection_counts,
        "total_backfilled_chunks": sum(step_counts.values()),
    }


def main() -> None:
    result = run_backfill()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()