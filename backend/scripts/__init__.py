"""compat package: 旧 scripts.* 路径转发到 crawler/scripts 与 legacy/scripts。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_backend_dir = _pkg_dir.parent

__path__ = [str(_pkg_dir)]
for _target in (_backend_dir / "crawler" / "scripts", _backend_dir / "legacy" / "scripts"):
    if _target.exists():
        __path__.append(str(_target))

__all__ = [
    "build_vector_store",
    "import_financial_data",
    "import_macro_data",
    "import_research_reports",
    "import_stock_data",
    "test_retrieval",
]