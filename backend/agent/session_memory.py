"""进程内会话记忆缓存。

每个 session 维护一份压缩摘要 + 最近 N 条原始消息。
当原始消息超过阈值时，调用 LLM 将旧消息压缩成摘要，避免 token 线性增长。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_RAW_KEEP = 6        # 始终保留最近 N 条原始消息不压缩
_COMPRESS_THRESHOLD = 14  # 原始消息超过此数量时触发压缩
_TTL_SECONDS = 1800  # 缓存 30 分钟无访问则过期


@dataclass
class _SessionMemory:
    summary: str = ""                          # 压缩后的历史摘要
    recent: list[dict[str, str]] = field(default_factory=list)  # 最近 N 条原始消息
    last_access: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_access = time.time()

    def is_expired(self) -> bool:
        return time.time() - self.last_access > _TTL_SECONDS


class SessionMemoryCache:
    """进程级单例，管理所有 session 的记忆状态。"""

    def __init__(self) -> None:
        self._store: dict[int, _SessionMemory] = {}

    # ── 公开接口 ──────────────────────────────────────────────────────────

    def build_history(
        self,
        session_id: int,
        db_messages: list[dict[str, str]],
        *,
        llm_compress_fn: Any = None,
    ) -> tuple[str, list[dict[str, str]]]:
        """返回 (summary, recent_messages)，供 build_messages 使用。

        - 若缓存命中且未过期，直接返回缓存内容。
        - 若 db_messages 超过压缩阈值，触发压缩并更新缓存。
        - 否则直接用 db_messages 的最近 N 条。
        """
        self._evict_expired()
        mem = self._store.get(session_id)

        # 缓存命中：直接用缓存，不再读 db_messages
        if mem is not None and not mem.is_expired():
            mem.touch()
            return mem.summary, mem.recent

        # 缓存未命中：从 db_messages 重建
        return self._rebuild(session_id, db_messages, llm_compress_fn=llm_compress_fn)

    def append(
        self,
        session_id: int,
        role: str,
        content: str,
        *,
        llm_compress_fn: Any = None,
    ) -> None:
        """每轮对话结束后追加新消息到缓存，避免下轮重新查库。

        当 recent 超过压缩阈值时，将旧消息压缩进 summary，保持 recent
        始终不超过 _RAW_KEEP 条，防止长会话 token 线性增长。
        """
        mem = self._store.get(session_id)
        if mem is None:
            return
        mem.recent.append({"role": role, "content": content})
        mem.touch()

        # 超过阈值时压缩旧消息，保持 recent 在 _RAW_KEEP 以内
        if len(mem.recent) > _COMPRESS_THRESHOLD:
            old = mem.recent[:-_RAW_KEEP]
            mem.recent = mem.recent[-_RAW_KEEP:]
            if llm_compress_fn is not None:
                new_summary = _safe_compress(old, llm_compress_fn)
            else:
                new_summary = _fallback_summary(old)
            # 将新摘要追加到已有摘要后面
            if mem.summary:
                mem.summary = mem.summary + "\n" + new_summary
            else:
                mem.summary = new_summary

    def invalidate(self, session_id: int) -> None:
        """删除 session 时清除缓存。"""
        self._store.pop(session_id, None)

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _rebuild(
        self,
        session_id: int,
        db_messages: list[dict[str, str]],
        *,
        llm_compress_fn: Any,
    ) -> tuple[str, list[dict[str, str]]]:
        if len(db_messages) <= _RAW_KEEP:
            mem = _SessionMemory(summary="", recent=list(db_messages))
            self._store[session_id] = mem
            return mem.summary, mem.recent

        if len(db_messages) > _COMPRESS_THRESHOLD and llm_compress_fn is not None:
            old = db_messages[:-_RAW_KEEP]
            recent = db_messages[-_RAW_KEEP:]
            summary = _safe_compress(old, llm_compress_fn)
        else:
            old = db_messages[:-_RAW_KEEP]
            recent = db_messages[-_RAW_KEEP:]
            summary = _fallback_summary(old)

        mem = _SessionMemory(summary=summary, recent=recent)
        self._store[session_id] = mem
        return summary, recent

    def _evict_expired(self) -> None:
        expired = [sid for sid, m in self._store.items() if m.is_expired()]
        for sid in expired:
            del self._store[sid]


def _safe_compress(messages: list[dict[str, str]], compress_fn: Any) -> str:
    try:
        return compress_fn(messages)
    except Exception as exc:
        logger.warning("Memory compression failed, using fallback: %s", exc)
        return _fallback_summary(messages)


def _fallback_summary(messages: list[dict[str, str]]) -> str:
    """LLM 不可用时，用最后几条消息拼一个简单摘要。"""
    lines = []
    for m in messages[-4:]:
        role = "用户" if m.get("role") == "user" else "助手"
        content = str(m.get("content") or "")[:120]
        lines.append(f"{role}：{content}")
    if not lines:
        return ""
    return "【历史摘要】\n" + "\n".join(lines)


# 进程级单例
_cache = SessionMemoryCache()


def get_session_memory_cache() -> SessionMemoryCache:
    return _cache


__all__ = ["SessionMemoryCache", "get_session_memory_cache"]
