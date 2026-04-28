"""Canonical backend filesystem paths rooted at backend/."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DATA_DIR = BACKEND_ROOT / "local_data"
PHARMA_COMPANIES_DATA_DIR = LOCAL_DATA_DIR / "pharma_companies"
CHROMA_DB_DIR = (BACKEND_ROOT / "chroma_db").resolve()
KNOWLEDGE_STORE_FILE = (BACKEND_ROOT / "knowledge_store.json").resolve()
CRAWLER_ROOT = BACKEND_ROOT / "crawler"
CRAWLER_STAGING_DIR = CRAWLER_ROOT / "staging"
CRAWLER_SCRIPTS_DIR = CRAWLER_ROOT / "scripts"

__all__ = [
    "BACKEND_ROOT",
    "LOCAL_DATA_DIR",
    "PHARMA_COMPANIES_DATA_DIR",
    "CHROMA_DB_DIR",
    "KNOWLEDGE_STORE_FILE",
    "CRAWLER_ROOT",
    "CRAWLER_STAGING_DIR",
    "CRAWLER_SCRIPTS_DIR",
]