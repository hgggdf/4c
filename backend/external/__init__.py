"""compat package: 旧 external.* 路径转发到 crawler/*。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_backend_dir = _pkg_dir.parent

__path__ = [str(_pkg_dir)]
for _target in (
	_backend_dir / "crawler" / "clients",
	_backend_dir / "crawler" / "scrapers",
	_backend_dir / "crawler" / "parsers",
):
	if _target.exists():
		__path__.append(str(_target))

__all__ = ["akshare_client", "pdf_parser", "tushare_client", "web_scraper"]
