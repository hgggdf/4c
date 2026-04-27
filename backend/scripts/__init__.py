"""后端脚本包，聚合正式脚本与 crawler 脚本入口。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_backend_dir = _pkg_dir.parent

__path__ = [str(_pkg_dir)]
for _target in (_backend_dir / "crawler" / "scripts",):
    if _target.exists():
        __path__.append(str(_target))

__all__ = [
    "import_research_reports",
    "test_retrieval",
]