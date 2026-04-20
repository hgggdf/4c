from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_inner_dir = _pkg_dir.parent / "core" / "repositories"
__path__ = [str(_pkg_dir)]
if _inner_dir.exists():
    __path__.append(str(_inner_dir))

from core.core.repositories import *  # noqa: F401,F403
