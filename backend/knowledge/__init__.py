"""compat package: 旧 knowledge.* 导入路径转发到 legacy/compat/knowledge。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_compat_dir = _pkg_dir.parent / "legacy" / "compat" / "knowledge"

__path__ = [str(_pkg_dir)]
if _compat_dir.exists():
    __path__.append(str(_compat_dir))

try:
    from . import retriever, store, sync  # noqa: F401
except Exception:
    pass

__all__ = ["retriever", "store", "sync"]