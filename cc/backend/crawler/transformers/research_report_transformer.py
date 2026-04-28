"""
Research Report Transformer
负责将 raw/research_reports/eastmoney/ 下的研报 JSON
转换为：
  - staging/research_reports_phasec_live/research_reports_latest.json
  - staging/research_report_package.json（作为统一入口）

对应接口：/api/ingest/news-package
对应字段：news_raw
对应表：news_raw_hot
通过 news_type = "company_research_report" 或 "industry_research_report" 区分
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseTransformer


class ResearchReportTransformer(BaseTransformer):
    DATA_CATEGORY = "research_report"
    # staging 路径：规范要求放在 research_reports_phasec_live/
    STAGING_FILENAME = "research_reports_phasec_live/research_reports_latest.json"
    TARGET_ENDPOINT = "/api/ingest/news-package"
    TARGET_TABLE = "news_raw_hot"
    INGEST_PACKAGE = "news-package"
    INGEST_FIELD = "news_raw"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/research_reports/eastmoney/ 下的所有研报文件
        包括 merged_reports_*.json, stock_*.json, industry_*.json
        """
        reports_dir = self.raw_dir / "research_reports" / "eastmoney"
        if not reports_dir.exists():
            return []

        raw_files = []
        for pattern in ("merged_reports_*.json", "stock_*.json", "industry_*.json"):
            raw_files.extend(reports_dir.glob(pattern))

        # 按文件名日期过滤
        if begin_date or end_date:
            filtered = []
            for f in raw_files:
                # 文件名格式：merged_reports_2026-03-24_2026-04-23.json
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
        将研报 raw 格式转换为标准 staging 格式

        raw 格式（已确认）：
        {
          "meta": {
            "scope": "industry",  // 或 "stock"
            "target": "医药生物",
            "begin_date": "2026-03-24",
            "end_date": "2026-04-23",
            ...
          },
          "items": [
            {
              "title": "...",
              "org": "华源证券",
              "publish_date": "2026-04-22",
              "stock_code": null,      // 行业研报无股票代码
              "stock_name": null,
              "industry": "生物制品",
              "rating": "看好(Overweight)",
              "summary": "...",
              "source_site": "eastmoney",
              "report_type": "industry",  // 或 "stock"
              "source_url": "https://...",
              "pdf_url": "https://...",
              "info_code": "AP202604221821437435",
              "content": "...",
              "_content_enriched": true,
              ...
            }
          ]
        }

        staging news_raw 字段：
        news_uid, title, publish_time, source_name, source_url,
        author_name, content, news_type, language, file_hash
        """
        records = []
        items = raw_data.get("items", [])
        meta = raw_data.get("meta", {})
        scope = meta.get("scope", "unknown")  # "stock" 或 "industry"

        for item in items:
            title = item.get("title", "")
            if not title:
                continue

            # 生成唯一 news_uid
            news_uid = self._generate_news_uid(item, raw_path)

            # 判断研报类型
            stock_code = item.get("stock_code")
            if stock_code:
                news_type = "company_research_report"
            else:
                news_type = "industry_research_report"

            # publish_time 标准化
            publish_time = self._normalize_datetime(item.get("publish_date"))

            # file_hash 从 item 中取，没有则用 info_code 生成
            file_hash = item.get("file_hash")
            if not file_hash:
                info_code = item.get("info_code", "")
                if info_code:
                    file_hash = hashlib.md5(info_code.encode()).hexdigest()

            records.append({
                "news_uid": news_uid,
                "title": title,
                "publish_time": publish_time,
                "source_name": item.get("org") or item.get("source_site", "东方财富研报"),
                "source_url": item.get("source_url"),
                "author_name": item.get("org"),  # org 即机构/作者
                "content": item.get("content") or item.get("summary"),
                "news_type": news_type,
                "language": "zh",
                "file_hash": file_hash,
                # 额外字段（staging 有，但不写入 news_raw_hot）
                "_meta_scope": scope,
                "_meta_target": meta.get("target"),
                "_stock_code": stock_code,
                "_industry": item.get("industry"),
                "_rating": item.get("rating"),
                "_pdf_url": item.get("pdf_url"),
            })

        return records

    def build_staging_payload(self, records: list[dict]) -> dict:
        """
        构建 staging payload
        news-package 结构：6个字段
        这一步只填充 news_raw，其他为空
        """
        return {
            "macro_indicators": [],
            "news_raw": records,
            "news_structured": [],
            "news_industry_maps": {},
            "news_company_maps": {},
            "industry_impact_events": [],
            "sync_vector_index": True,
        }

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _generate_news_uid(self, item: dict, raw_path: Path) -> str:
        """生成唯一 news_uid"""
        info_code = item.get("info_code", "")
        if info_code:
            return f"rr_{info_code}"
        # 兜底：用标题+日期的 hash
        title = item.get("title", "")
        publish_date = item.get("publish_date", "")
        raw = f"{title}_{publish_date}_{raw_path.name}".encode()
        return f"rr_{hashlib.md5(raw).hexdigest()[:12]}"

    def _normalize_datetime(self, value) -> str | None:
        """标准化日期时间为 YYYY-MM-DD HH:MM:SS"""
        if not value:
            return None
        text = str(value).strip()
        # 已经是 YYYY-MM-DD
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return f"{text} 00:00:00"
        # YYYYMMDD
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:8]} 00:00:00"
        # 已经是 YYYY-MM-DD HH:MM:SS
        if len(text) >= 19:
            return text[:19]
        return None
