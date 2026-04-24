"""
ingest_center / common.py
=======================

公共工具模块。

职责：
    提供第3、4层 job 共用的最小公共工具，不依赖具体业务表。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def now_iso() -> str:
    """返回当前 UTC ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str) -> None:
    """确保目录存在，不存在则递归创建。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_json(path: str, data: dict) -> None:
    """将字典写入 JSON 文件，自动确保目录存在。"""
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_receipt(receipt_path: str, data: dict) -> str:
    """
    将 receipt 字典写入指定路径。

    Args:
        receipt_path: receipt 完整文件路径。
        data: receipt 字典。

    Returns:
        写入的文件路径。
    """
    write_json(receipt_path, data)
    return receipt_path
