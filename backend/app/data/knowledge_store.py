"""
向量知识库：使用 ChromaDB + BGE embedding 实现语义检索
同时保留 TF-IDF 作为兜底
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CHROMA_PATH = BACKEND_ROOT / "chroma_db"
STORE_PATH = BACKEND_ROOT / "knowledge_store.json"

_embedding_model = None
_chroma_client = None
_collection = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _embedding_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _chroma_client.get_or_create_collection(
            name="pharma_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    vecs = model.encode(texts, normalize_embeddings=True)
    return vecs.tolist()


def _chunk(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


class VectorKnowledgeStore:
    """ChromaDB 向量知识库，支持语义检索"""

    def add(self, text: str, meta: dict | None = None) -> int:
        """切块、向量化并存入 ChromaDB，返回写入块数"""
        collection = _get_collection()
        chunks = _chunk(text)
        if not chunks:
            return 0

        embeddings = _embed(chunks)
        meta = meta or {}

        # 生成唯一 ID（基于内容 hash）
        import hashlib
        ids = [
            hashlib.md5(f"{meta.get('source','')}{chunk}".encode()).hexdigest()
            for chunk in chunks
        ]

        # ChromaDB upsert 避免重复
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[meta] * len(chunks),
        )
        return len(chunks)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """向量语义检索"""
        collection = _get_collection()
        if collection.count() == 0:
            return []

        q_vec = _embed([query])[0]
        results = collection.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)  # cosine distance -> similarity
            if score > 0.3:
                hits.append({"text": doc, "score": score, "meta": meta})
        return hits

    def count(self) -> int:
        return _get_collection().count()


# ── 兼容旧接口的 KnowledgeStore（TF-IDF 兜底） ──────────────────────────────

import math
from collections import defaultdict


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
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


class KnowledgeStore:
    """TF-IDF 知识库（兜底，向量库不可用时使用）"""

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

    def add(self, text: str, meta: dict | None = None) -> None:
        for chunk in _chunk(text):
            self.docs.append({"text": chunk, "meta": meta or {}})
        self._rebuild_index()
        self._save()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.docs:
            return []
        q_tokens = _tokenize(query)
        q_vec = _tfidf_vector(q_tokens, self.vocab, self.idf)
        scores = [(i, _cosine(q_vec, v)) for i, v in enumerate(self.vectors)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"text": self.docs[i]["text"], "score": round(s, 4), "meta": self.docs[i]["meta"]}
            for i, s in scores[:top_k]
            if s > 0.05
        ]

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


# ── 单例 ──────────────────────────────────────────────────────────────────────

_vector_store: VectorKnowledgeStore | None = None
_tfidf_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    """兼容旧调用，返回 TF-IDF store"""
    global _tfidf_store
    if _tfidf_store is None:
        _tfidf_store = KnowledgeStore()
    return _tfidf_store


def get_vector_store() -> VectorKnowledgeStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorKnowledgeStore()
    return _vector_store
