"""重建研报向量集合并回填已有研报数据。

用法:
    python scripts/rebuild_research_report_collection.py
    python scripts/rebuild_research_report_collection.py --skip-backfill
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

import chromadb

from app.core.database.session import SessionLocal
from app.knowledge import store as knowledge_store_module
from app.knowledge.store import ACTIVE_COLLECTIONS
from app.knowledge.sync import sync_research_reports
from app.paths import CHROMA_DB_DIR

DOC_TYPE = "report"
COLLECTION_NAME = ACTIVE_COLLECTIONS[DOC_TYPE]
COLLECTION_METADATA = {
    "hnsw:space": "cosine",
    "hnsw:batch_size": 5000,
    "hnsw:sync_threshold": 5000,
}
REOPEN_CHECK_TIMEOUT_SECONDS = 180
REOPEN_CHECK_INTERVAL_SECONDS = 2


def _build_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(CHROMA_DB_DIR))


def _close_client(client: chromadb.PersistentClient | None) -> None:
    if client is None:
        return
    try:
        client.close()
    except Exception:
        pass


def _safe_collection_count(client: chromadb.PersistentClient, collection_name: str) -> dict:
    collection_names = {collection.name for collection in client.list_collections()}
    if collection_name not in collection_names:
        return {"count": 0, "error": None, "exists": False}
    try:
        count = client.get_collection(collection_name).count()
        return {"count": int(count), "error": None, "exists": True}
    except Exception as exc:
        return {"count": None, "error": str(exc), "exists": True}


def _collect_counts() -> dict[str, dict]:
    client = _build_client()
    try:
        return {
            doc_type: _safe_collection_count(client, col_name)
            for doc_type, col_name in ACTIVE_COLLECTIONS.items()
        }
    finally:
        _close_client(client)


def _recreate_collection() -> dict:
    client = _build_client()
    recreated_client: chromadb.PersistentClient | None = None
    try:
        existing = _safe_collection_count(client, COLLECTION_NAME)
        deleted = False
        if existing["exists"]:
            client.delete_collection(COLLECTION_NAME)
            deleted = True
        recreated_client = _build_client()
        recreated = recreated_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata=COLLECTION_METADATA,
        )
    finally:
        _close_client(client)
        _close_client(recreated_client)
    return {
        "deleted_existing": deleted,
        "recreated_name": recreated.name,
        "metadata": COLLECTION_METADATA,
        "after_recreate": _collect_counts()[DOC_TYPE],
    }


def _backfill_reports() -> int:
    with SessionLocal() as db:
        try:
            backfilled = int(sync_research_reports(db, is_hot=True))
            db.commit()
            return backfilled
        except Exception:
            db.rollback()
            raise


def _close_store_clients() -> None:
    _close_client(getattr(knowledge_store_module, "_chroma_client", None))
    knowledge_store_module._chroma_client = None
    knowledge_store_module._collection_cache.clear()


def _count_in_fresh_process() -> dict:
    code = (
        "import json; import chromadb; "
        "from app.paths import CHROMA_DB_DIR; "
        f"client = chromadb.PersistentClient(path=r'{CHROMA_DB_DIR}'); "
        f"collection = client.get_collection('{COLLECTION_NAME}'); "
        "print(json.dumps({'count': int(collection.count()), 'error': None}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode == 0:
        return json.loads(stdout)
    return {
        "count": None,
        "error": stderr or stdout or f"fresh-process count failed with exit code {completed.returncode}",
    }


def _wait_for_reopenable_collection(expected_min_count: int) -> dict:
    deadline = time.monotonic() + REOPEN_CHECK_TIMEOUT_SECONDS
    last_result = {"count": None, "error": "fresh-process reopen check not started"}
    while time.monotonic() < deadline:
        last_result = _count_in_fresh_process()
        count = last_result.get("count")
        if isinstance(count, int) and count >= expected_min_count and not last_result.get("error"):
            return {
                "count": count,
                "error": None,
                "expected_min_count": expected_min_count,
                "timeout_seconds": REOPEN_CHECK_TIMEOUT_SECONDS,
            }
        time.sleep(REOPEN_CHECK_INTERVAL_SECONDS)
    raise RuntimeError(
        "research_report collection is still not reopenable in a fresh process: "
        f"{json.dumps(last_result, ensure_ascii=False)}"
    )


def run_repair(*, skip_backfill: bool = False) -> dict:
    before = _collect_counts()
    recreate_result = _recreate_collection()

    backfilled = 0
    if not skip_backfill:
        backfilled = _backfill_reports()

    _close_store_clients()
    reopen_validation = _wait_for_reopenable_collection(backfilled)
    after = _collect_counts()
    return {
        "chroma_path": str(CHROMA_DB_DIR),
        "doc_type": DOC_TYPE,
        "collection_name": COLLECTION_NAME,
        "before": before,
        "recreate": recreate_result,
        "backfilled_chunks": backfilled,
        "reopen_validation": reopen_validation,
        "after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the research_report Chroma collection and backfill vectors."
    )
    parser.add_argument(
        "--skip-backfill", action="store_true",
        help="Only drop and recreate the collection without backfilling vectors",
    )
    args = parser.parse_args()
    result = run_repair(skip_backfill=args.skip_backfill)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
