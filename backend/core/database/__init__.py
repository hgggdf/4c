from pathlib import Path as _Path
import importlib as _importlib
import sys as _sys

_pkg_dir = _Path(__file__).resolve().parent
_inner_dir = _pkg_dir.parent / "core" / "database"
__path__ = [str(_pkg_dir)]
if _inner_dir.exists():
    __path__.append(str(_inner_dir))

_inner_pkg = "core.core.database"
for _submodule in ["base", "session", "init_db", "models"]:
    _sys.modules[f"{__name__}.{_submodule}"] = _importlib.import_module(f"{_inner_pkg}.{_submodule}")
