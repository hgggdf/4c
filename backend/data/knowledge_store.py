"""
轻量向量知识库：用 numpy 余弦相似度实现语义检索，无需 faiss
文档分块 -> 向量化（调用 Claude Embeddings 或简单 TF-IDF）-> 检索
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

STORE_PATH = Path(__file__).parent.parent / "knowledge_store.json"


def _tokenize(text: str) -> list[str]:
    """简单中文分词：按字符 + 常见词边界切分"""
    text = re.sub(r"\s+", " ", text)
    tokens = re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9]+", text)
    return tokens


def _tfidf_vector(tokens: list[str], vocab: dict[str, int], idf: dict[str, float]) -> list[float]:
    tf: dict[str, float] = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    n = len(tokens) or 1
    vec = [0.0] * len(vocab)
    for t, cnt in tf.items():
        if t in vocab:
            vec[vocab[t]] = (cnt / n) * idf.get(t, 1.0)
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class KnowledgeStore:
    def __init__(self) -> None:
        self.docs: list[dict] = []   # {"text": ..., "meta": {...}}
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.vectors: list[list[float]] = []
        if STORE_PATH.exists():
            self._load()

    def _rebuild_index(self) -> None:
        all_tokens = [_tokenize(d["text"]) for d in self.docs]
        # 构建词表
        vocab_set: set[str] = set()
        for tokens in all_tokens:
            vocab_set.update(tokens)
        self.vocab = {w: i for i, w in enumerate(sorted(vocab_set))}
        # 计算 IDF
        n = len(self.docs) or 1
        df: dict[str, int] = defaultdict(int)
        for tokens in all_tokens:
            for t in set(tokens):
                df[t] += 1
        self.idf = {t: math.log(n / (cnt + 1)) + 1 for t, cnt in df.items()}
        # 计算向量
        self.vectors = [_tfidf_vector(tokens, self.vocab, self.idf) for tokens in all_tokens]

    def add(self, text: str, meta: dict | None = None) -> None:
        """添加一段文本到知识库"""
        chunks = self._chunk(text)
        for chunk in chunks:
            self.docs.append({"text": chunk, "meta": meta or {}})
        self._rebuild_index()
        self._save()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """语义检索，返回最相关的 top_k 段落"""
        if not self.docs:
            return []
        q_tokens = _tokenize(query)
        q_vec = _tfidf_vector(q_tokens, self.vocab, self.idf)
        scores = [(i, _cosine(q_vec, v)) for i, v in enumerate(self.vectors)]
        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for i, score in scores[:top_k]:
            if score > 0.05:
                results.append({"text": self.docs[i]["text"], "score": round(score, 4), "meta": self.docs[i]["meta"]})
        return results

    def _chunk(self, text: str, size: int = 400, overlap: int = 50) -> list[str]:
        """将长文本切成带重叠的块"""
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


_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store
