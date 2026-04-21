"""compat package: 旧 modules.* API 路径转发到 legacy/modules。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_legacy_dir = _pkg_dir.parent / "legacy" / "modules"

__path__ = [str(_pkg_dir)]
if _legacy_dir.exists():
    __path__.append(str(_legacy_dir))

__all__ = ["analysis", "chat", "company", "stock"]