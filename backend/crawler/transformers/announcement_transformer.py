"""
Announcement Transformer
负责将 raw/announcements/<exchange>/ 下的公告 JSON
转换为 staging/announcement_package.json

对应接口：/api/ingest/announcement-package
对应字段：raw_announcements
对应表：announcement_raw_hot
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import BaseTransformer


class AnnouncementTransformer(BaseTransformer):
    DATA_CATEGORY = "announcement_raw"
    STAGING_FILENAME = "announcement_package.json"
    TARGET_ENDPOINT = "/api/ingest/announcement-package"
    TARGET_TABLE = "announcement_raw_hot"
    INGEST_PACKAGE = "announcement-package"
    INGEST_FIELD = "raw_announcements"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/announcements/ 下的所有 exchange 子目录
        收集所有 _<begin>_<end>.json 文件
        """
        announcements_dir = self.raw_dir / "announcements"
        if not announcements_dir.exists():
            return []

        raw_files = []
        for exchange_dir in announcements_dir.iterdir():
            if not exchange_dir.is_dir():
                continue
            # 匹配格式: {stock_code}_{begin}_{end}.json
            for f in exchange_dir.glob("*.json"):
                raw_files.append(f)

        # 按日期过滤（从文件名提取日期范围）
        if begin_date or end_date:
            filtered = []
            for f in raw_files:
                parts = f.stem.split("_")
                if len(parts) >= 3:
                    file_begin = parts[-2]
                    file_end = parts[-1]
                    if begin_date and file_end < begin_date:
                        continue
                    if end_date and file_begin > end_date:
                        continue
                filtered.append(f)
            raw_files = filtered

        return sorted(raw_files)

    def load_raw(self, raw_path: Path) -> dict:
        """读取 raw 文件"""
        return json.loads(raw_path.read_text(encoding="utf-8"))

    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        将公告 raw 格式转换为标准 staging 格式

        raw 格式（已确认）：
        {
          "success": true,
          "source": "sse",
          "items": [
            {
              "stock_code": "600276",
              "title": "...",
              "publish_date": "2026-04-23",
              "exchange": "SSE",
              "announcement_type": "公告",
              "source_url": "http://...",
              "source_type": "sse_announcement_api",
              "content": "...",
              "file_hash": "md5hex",
              "_content_enriched": false,
              "_content_enrich_error": "..."
            }
          ]
        }

        staging 字段：
        stock_code, title, publish_date, announcement_type, exchange,
        content, source_url, source_type, file_hash
        """
        records = []
        items = raw_data.get("items", [])

        for item in items:
            stock_code = item.get("stock_code", "")
            title = item.get("title", "")
            if not stock_code or not title:
                continue

            records.append({
                "stock_code": stock_code,
                "title": title,
                "publish_date": self._normalize_date(item.get("publish_date")),
                "announcement_type": item.get("announcement_type"),
                "exchange": item.get("exchange"),
                "content": item.get("content"),
                "source_url": item.get("source_url"),
                "source_type": item.get("source_type", "exchange_announcement_api"),
                "file_hash": item.get("file_hash"),
            })

        return records

    def build_staging_payload(self, records: list[dict]) -> dict:
        """
        构建 staging payload
        announcement-package 结构：6个字段都是数组
        这一步只填充 raw_announcements，其他为空数组
        """
        return {
            "raw_announcements": records,
            "structured_announcements": [],
            "drug_approvals": [],
            "clinical_trials": [],
            "procurement_events": [],
            "regulatory_risks": [],
            "sync_vector_index": True,
        }

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _normalize_date(self, value) -> str | None:
        """标准化日期为 YYYY-MM-DD"""
        if not value:
            return None
        text = str(value).strip()
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return text
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        return None
