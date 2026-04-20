from pathlib import Path as _Path
import importlib as _importlib
import sys as _sys

_pkg_dir = _Path(__file__).resolve().parent
_inner_dir = _pkg_dir.parent.parent / "core" / "database" / "models"
__path__ = [str(_pkg_dir)]
if _inner_dir.exists():
    __path__.append(str(_inner_dir))

_inner_pkg = "core.core.database.models"
_inner = _importlib.import_module(_inner_pkg)

for _name in getattr(_inner, "__all__", []):
    globals()[_name] = getattr(_inner, _name)

for _submodule in [
    "announcement_hot",
    "archive",
    "company",
    "financial_hot",
    "macro_hot",
    "news_hot",
    "summary_cache",
    "user",
]:
    _sys.modules[f"{__name__}.{_submodule}"] = _importlib.import_module(f"{_inner_pkg}.{_submodule}")

__all__ = list(getattr(_inner, "__all__", []))
