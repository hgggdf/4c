from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_app_dir = _pkg_dir.parent.parent / "app" / "core"

__path__ = [str(_pkg_dir)]
if _app_dir.exists():
    __path__.append(str(_app_dir))

try:
    from app.core import database, repositories, utils  # noqa: F401
except Exception:
    pass

__all__ = ["database", "repositories", "utils"]