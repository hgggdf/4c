"""
ingest_center / file_checks.py
==============================

文件存在性与完整性校验模块。

职责：
    对 manifest 中声明的文件进行落地检查：
    - 文件是否真实存在
    - sha256 校验值是否匹配
"""

import hashlib
import os


def ensure_file_exists(path: str) -> None:
    """
    检查给定路径的文件是否存在且为普通文件。

    Args:
        path: 待检查的文件路径。

    Raises:
        FileNotFoundError: 文件不存在或不是普通文件。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"file not found: {path}")


def compute_sha256(path: str) -> str:
    """
    计算文件的 sha256 摘要。

    Args:
        path: 文件路径。

    Returns:
        小写十六进制 sha256 字符串。
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(path: str, expected: str) -> None:
    """
    校验文件 sha256 是否与预期一致。

    Args:
        path: 文件路径。
        expected: 预期的 sha256 值。

    Raises:
        ValueError: 校验不一致。
    """
    actual = compute_sha256(path)
    if actual != expected:
        raise ValueError(
            f"sha256 mismatch for {path}: expected {expected}, got {actual}"
        )
