from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_inner_pkg = _pkg_dir / "core"
__path__ = [str(_pkg_dir)]
if _inner_pkg.exists():
    __path__.append(str(_inner_pkg))

try:
    from .core import database, repositories, utils  # noqa: F401
except Exception:
    pass

__all__ = ["database", "repositories", "utils"]
