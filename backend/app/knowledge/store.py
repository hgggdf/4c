from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from app.paths import BACKEND_ROOT, CHROMA_DB_DIR, KNOWLEDGE_STORE_FILE

PROJECT_ROOT = BACKEND_ROOT
CHROMA_PATH = CHROMA_DB_DIR
STORE_PATH = KNOWLEDGE_STORE_FILE

_embedding_model = None
_chroma_client = None
_collection_cache: dict[str, Any] = {}

COLLECTION_MAP = {
    "announcement": "announcement_chunks",
    "financial_note": "financial_note_chunks",
    "report": "report_chunks",
    "policy": "policy_chunks",
    "news": "news_chunks",
    "company_profile": "company_profile_chunks",
}


@dataclass
class ChunkMetadata:
    doc_type: str
    doc_id: str
    stock_code: str = ""
    stock_name: str = ""
    title: str = ""
    publish_date: str = ""
    category: str = ""
    topic_category: str = ""
    signal_type: str = ""
    risk_level: str = ""
    impact_level: str = ""
    impact_direction: str = ""
    impact_horizon: str = ""
    source_type: str = ""
    source_url: str = ""
    source_table: str = ""
    source_pk: str = ""
    industry_code: str = ""
    industry_name: str = ""
    drug_name: str = ""
    indication: str = ""
    trial_phase: str = ""
    event_type: str = ""
    is_hot: int = 1

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: ("" if v is None else v) for k, v in data.items()}


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _embedding_model


def _get_collection_name(doc_type: str) -> str:
    return COLLECTION_MAP.get(doc_type, "pharma_knowledge")


def _get_collection(collection_name: str):
    global _chroma_client, _collection_cache
    if collection_name in _collection_cache:
        return _collection_cache[collection_name]

    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collection = _chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    _collection_cache[collection_name] = collection
    return collection


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    vecs = model.encode(texts, normalize_embeddings=True)
    return vecs.tolist()


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    step = max(1, size - overlap)
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += step
    return chunks


def _build_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    if not filters:
        return None

    clauses = []
    for key, value in filters.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            if not value:
                continue
            clauses.append({key: {"$in": list(value)}})
        else:
            clauses.append({key: value})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _merge_filters(base: dict[str, Any] | None, extra: dict[str, Any] | None) -> dict[str, Any] | None:
    merged = dict(base or {})
    for k, v in (extra or {}).items():
        if v is not None and v != "":
            merged[k] = v
    return merged or None


class VectorKnowledgeStore:
    """底层向量知识库。"""

    def add_document(
        self,
        text: str,
        doc_type: str,
        metadata: dict[str, Any],
        doc_id: str | None = None,
    ) -> int:
        chunks = chunk_text(text)
        if not chunks:
            return 0

        try:
            collection_name = _get_collection_name(doc_type)
            collection = _get_collection(collection_name)
            embeddings = _embed(chunks)
        except Exception:
            return 0

        meta = dict(metadata)
        meta["doc_type"] = doc_type
        if doc_id:
            meta["doc_id"] = doc_id

        base_doc_id = meta.get("doc_id", "doc")
        ids = [
            hashlib.md5(f"{base_doc_id}_{i}_{chunk}".encode("utf-8")).hexdigest()
            for i, chunk in enumerate(chunks)
        ]

        metadatas = []
        for i, _ in enumerate(chunks):
            m = dict(meta)
            m["chunk_index"] = i
            metadatas.append(m)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    def _query_collection(
        self,
        doc_type: str,
        query_vec: list[float],
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            collection = _get_collection(_get_collection_name(doc_type))
            count = collection.count()
        except Exception:
            return []

        if count <= 0:
            return []

        where = _build_where(filters)
        try:
            results = collection.query(
                query_embeddings=[query_vec],
                n_results=min(top_k, count),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            try:
                results = collection.query(
                    query_embeddings=[query_vec],
                    n_results=min(top_k, count),
                    include=["documents", "metadatas", "distances"],
                )
            except Exception:
                return []

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        hits: list[dict[str, Any]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = round(1 - dist, 4)
            if score > 0.3:
                hits.append({"text": doc, "score": score, "meta": meta or {}})
        return hits

    def search(
        self,
        query: str,
        top_k: int = 3,
        doc_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        query = (query or "").strip()
        if not query:
            return []

        try:
            query_vec = _embed([query])[0]
        except Exception:
            return []

        target_doc_types = doc_types or list(COLLECTION_MAP.keys())
        hot_hits: list[dict] = []
        cold_hits: list[dict] = []

        # 优先热数据，再补冷数据
        for doc_type in target_doc_types:
            hot_hits.extend(
                self._query_collection(
                    doc_type,
                    query_vec,
                    top_k=top_k,
                    filters=_merge_filters(filters, {"is_hot": 1}),
                )
            )

        hot_hits.sort(key=lambda x: x["score"], reverse=True)
        if len(hot_hits) >= top_k:
            return hot_hits[:top_k]

        remain = max(1, top_k - len(hot_hits))
        for doc_type in target_doc_types:
            cold_hits.extend(
                self._query_collection(
                    doc_type,
                    query_vec,
                    top_k=max(top_k, remain),
                    filters=_merge_filters(filters, {"is_hot": 0}),
                )
            )

        cold_hits.sort(key=lambda x: x["score"], reverse=True)
        all_hits = hot_hits + cold_hits
        all_hits.sort(key=lambda x: x["score"], reverse=True)
        return all_hits[:top_k]

    def count(self, doc_type: str | None = None) -> int:
        try:
            if doc_type:
                return _get_collection(_get_collection_name(doc_type)).count()

            total = 0
            for dt in COLLECTION_MAP:
                total += _get_collection(_get_collection_name(dt)).count()
            return total
        except Exception:
            return 0

    def delete_by_source(
        self,
        *,
        doc_type: str,
        source_table: str,
        source_pks: list[str],
    ) -> int:
        try:
            collection = _get_collection(_get_collection_name(doc_type))
        except Exception:
            return 0

        deleted = 0
        for source_pk in source_pks:
            where = {
                "$and": [
                    {"source_table": source_table},
                    {"source_pk": str(source_pk)},
                ]
            }
            try:
                existing = collection.get(where=where, include=[])
                ids = existing.get("ids", []) if existing else []
                if ids:
                    collection.delete(ids=ids)
                    deleted += len(ids)
            except Exception:
                continue
        return deleted


# ---------------- TF-IDF fallback ----------------

def _tokenize(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "")
    return re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9]+", text)


def _tfidf_vector(tokens, vocab, idf):
    tf: dict[str, float] = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    n = len(tokens) or 1
    vec = [0.0] * len(vocab)
    for t, cnt in tf.items():
        if t in vocab:
            vec[vocab[t]] = (cnt / n) * idf.get(t, 1.0)
    return vec


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _match_filters(meta: dict | None, filters: dict[str, Any] | None, doc_types: list[str] | None = None) -> bool:
    meta = meta or {}
    if doc_types:
        if meta.get("doc_type") not in set(doc_types):
            return False

    for key, expected in (filters or {}).items():
        if expected is None or expected == "":
            continue
        actual = meta.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


class KnowledgeStore:
    """TF-IDF 兜底知识库。"""

    def __init__(self) -> None:
        self.docs: list[dict] = []
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.vectors: list[list[float]] = []
        if STORE_PATH.exists():
            self._load()

    def _rebuild_index(self) -> None:
        all_tokens = [_tokenize(d["text"]) for d in self.docs]
        vocab_set: set[str] = set()
        for tokens in all_tokens:
            vocab_set.update(tokens)

        self.vocab = {w: i for i, w in enumerate(sorted(vocab_set))}
        n = len(self.docs) or 1

        df: dict[str, int] = defaultdict(int)
        for tokens in all_tokens:
            for t in set(tokens):
                df[t] += 1

        self.idf = {t: math.log(n / (cnt + 1)) + 1 for t, cnt in df.items()}
        self.vectors = [_tfidf_vector(tokens, self.vocab, self.idf) for tokens in all_tokens]

    def add_document(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        for chunk in chunk_text(text):
            self.docs.append({"text": chunk, "meta": metadata or {}})
        self._rebuild_index()
        self._save()

    def search(
        self,
        query: str,
        top_k: int = 3,
        *,
        filters: dict[str, Any] | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        if not self.docs:
            return []

        q_tokens = _tokenize(query)
        q_vec = _tfidf_vector(q_tokens, self.vocab, self.idf)
        scores = [(i, _cosine(q_vec, v)) for i, v in enumerate(self.vectors)]
        scores.sort(key=lambda x: x[1], reverse=True)

        items = []
        for i, s in scores:
            if s <= 0.05:
                continue
            meta = self.docs[i].get("meta") or {}
            if not _match_filters(meta, filters=filters, doc_types=doc_types):
                continue
            items.append({"text": self.docs[i]["text"], "score": round(s, 4), "meta": meta})
            if len(items) >= top_k:
                break
        return items

    def delete_by_source(self, *, source_table: str, source_pks: list[str]) -> int:
        source_pk_set = {str(x) for x in source_pks}
        before = len(self.docs)
        self.docs = [
            d for d in self.docs
            if not (
                (d.get("meta") or {}).get("source_table") == source_table
                and str((d.get("meta") or {}).get("source_pk", "")) in source_pk_set
            )
        ]
        deleted = before - len(self.docs)
        if deleted:
            self._rebuild_index()
            self._save()
        return deleted

    def _save(self) -> None:
        data = {"docs": self.docs, "vocab": self.vocab, "idf": self.idf}
        STORE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        try:
            data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
            self.docs = data.get("docs", [])
            self.vocab = data.get("vocab", {})
            self.idf = data.get("idf", {})
            self._rebuild_index()
        except Exception:
            self.docs = []


_vector_store: VectorKnowledgeStore | None = None
_tfidf_store: KnowledgeStore | None = None


def get_vector_store() -> VectorKnowledgeStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorKnowledgeStore()
    return _vector_store


def get_store() -> KnowledgeStore:
    global _tfidf_store
    if _tfidf_store is None:
        _tfidf_store = KnowledgeStore()
    return _tfidf_store
