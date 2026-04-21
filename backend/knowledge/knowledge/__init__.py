from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_app_dir = _pkg_dir.parent.parent / "app" / "knowledge"

__path__ = [str(_pkg_dir)]
if _app_dir.exists():
    __path__.append(str(_app_dir))

try:
    from app.knowledge import retriever, store, sync  # noqa: F401
except Exception:
    pass

__all__ = ["retriever", "store", "sync"]