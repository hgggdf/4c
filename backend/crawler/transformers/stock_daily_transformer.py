"""
Stock Daily Transformer
负责将 raw/financial_data/akshare/stock_daily_akshare_*.json
转换为 staging/stock_daily_package.json

对应接口：/api/ingest/financial-package
对应字段：stock_daily
对应表：stock_daily_hot
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseTransformer


class StockDailyTransformer(BaseTransformer):
    DATA_CATEGORY = "stock_daily"
    STAGING_FILENAME = "stock_daily_package.json"
    TARGET_ENDPOINT = "/api/ingest/financial-package"
    TARGET_TABLE = "stock_daily_hot"
    INGEST_PACKAGE = "financial-package"
    INGEST_FIELD = "stock_daily"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/financial_data/akshare/ 下的 stock_daily 文件
        按日期范围过滤
        """
        raw_akshare = self.raw_dir / "financial_data" / "akshare"
        if not raw_akshare.exists():
            return []

        pattern = "stock_daily_akshare_*.json"
        all_files = sorted(raw_akshare.glob(pattern))

        if not begin_date and not end_date:
            return all_files

        # 按日期过滤
        filtered = []
        for f in all_files:
            # 文件名格式：stock_daily_akshare_<stock_code>_<begin>_<end>.json
            # 或 stock_daily_akshare_<begin>_<end>.json（某些命名方式）
            name = f.stem
            parts = name.split("_")
            # 取最后两个日期段
            if len(parts) >= 2:
                file_begin = parts[-2]
                file_end = parts[-1]
            else:
                continue

            if begin_date and file_end < begin_date:
                continue
            if end_date and file_begin > end_date:
                continue
            filtered.append(f)

        return filtered

    def load_raw(self, raw_path: Path) -> dict:
        """读取 raw 文件"""
        return self._load_json(raw_path)

    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        将 akshare stock_daily raw 格式转换为标准 staging 格式

        raw 字段：
          date, open, high, low, close, volume, amount, outstanding_share, turnover, _source

        staging 字段：
          stock_code, trade_date, open_price, high_price, low_price, close_price,
          volume, turnover, source_type
        """
        records = []

        # 从 meta 中获取 stock_code
        meta = raw_data.get("meta", {})
        stock_code = meta.get("stock_code", "")

        # 如果 meta 没有，尝试从文件名提取
        if not stock_code:
            stock_code = self._extract_stock_code(raw_path)

        raw_records = raw_data.get("records", [])
        for r in raw_records:
            trade_date = self._normalize_date(r.get("date"))
            if not trade_date:
                continue

            records.append({
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": self._to_decimal(r.get("open")),
                "high_price": self._to_decimal(r.get("high")),
                "low_price": self._to_decimal(r.get("low")),
                "close_price": self._to_decimal(r.get("close")),
                "volume": self._to_int(r.get("volume")),
                "turnover": self._to_decimal(r.get("amount")),  # amount → turnover
                "source_type": r.get("_source", "akshare_stock_zh_a_hist"),
            })

        return records

    def build_staging_payload(self, records: list[dict]) -> dict:
        """
        构建 staging payload
        financial-package 结构：8个字段都是数组
        这一步只填充 stock_daily，其他为空数组
        """
        return {
            "income_statements": [],
            "balance_sheets": [],
            "cashflow_statements": [],
            "financial_metrics": [],
            "financial_notes": [],
            "business_segments": [],
            "stock_daily": records,
            "sync_vector_index": False,
        }

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _load_json(self, path: Path) -> dict:
        import json as _json
        return _json.loads(path.read_text(encoding="utf-8"))

    def _extract_stock_code(self, raw_path: Path) -> str:
        """从文件名提取 stock_code"""
        # stock_daily_akshare_600276_2026-01-23_2026-04-23.json
        parts = raw_path.stem.split("_")
        if len(parts) >= 4:
            return parts[2]  # 第3个下划线分隔的字段是 stock_code
        return ""

    def _normalize_date(self, value) -> str | None:
        """标准化日期为 YYYY-MM-DD"""
        if not value:
            return None
        text = str(value).strip()
        # 已经是 YYYY-MM-DD
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return text
        # YYYYMMDD
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        return None

    def _to_decimal(self, value) -> float | None:
        """转为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _to_int(self, value) -> int | None:
        """转为整数"""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
