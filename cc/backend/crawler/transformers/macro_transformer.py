"""
Macro Transformer
负责将 raw/macro/stats_gov/<dbcode>/ 下的宏观 JSON
转换为 staging/macro_phasec_live/macro_indicators_latest.json

对应接口：/api/macro-write/macro-indicators
对应字段：items（直接 POST）
对应表：macro_indicator_hot

注意：宏观不走 news-package，直接调 /api/macro-write/macro-indicators
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import BaseTransformer


class MacroTransformer(BaseTransformer):
    DATA_CATEGORY = "macro"
    # staging 路径：规范要求放在 macro_phasec_live/
    STAGING_FILENAME = "macro_phasec_live/macro_indicators_latest.json"
    TARGET_ENDPOINT = "/api/macro-write/macro-indicators"
    TARGET_TABLE = "macro_indicator_hot"
    INGEST_PACKAGE = "macro-write"
    INGEST_FIELD = "macro_indicators"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/macro/stats_gov/ 下的所有 dbcode 子目录
        收集所有 macro_stats_gov_*.json 文件
        """
        stats_gov_dir = self.raw_dir / "macro" / "stats_gov"
        if not stats_gov_dir.exists():
            return []

        raw_files = []
        for dbcode_dir in stats_gov_dir.iterdir():
            if not dbcode_dir.is_dir():
                continue
            for f in dbcode_dir.glob("macro_stats_gov_*.json"):
                raw_files.append(f)

        # 按文件修改时间排序（取最新的）
        return sorted(raw_files)

    def load_raw(self, raw_path: Path) -> dict:
        """读取 raw 文件"""
        return json.loads(raw_path.read_text(encoding="utf-8"))

    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        将宏观 raw 格式转换为标准 staging 格式

        raw 格式（已确认）：
        {
          "meta": {
            "dbcode": "hgyd",
            "source": "stats_gov",
            "strategy_used": "requests/html",
            "fetch_time": "2026-04-23T05:20:19",
            "requested_indicators": [
              {"indicator_name": "...", "indicator_code": "A01010101", "unit": "%"}
            ],
            "raw_count": 15,
            "filtered_count": 15
          },
          "result": {
            "success": true,
            "data": {
              "series_results": [
                {
                  "indicator_name": "工业生产者出厂价格指数(上年同月=100)",
                  "period": "2026-03",
                  "value": "0.5",
                  "unit": "%",
                  "source_type": "stats_gov_release",
                  "source_url": "https://www.stats.gov.cn/..."
                }
              ]
            }
          }
        }

        staging 字段（直接 POST /api/macro-write/macro-indicators）：
        indicator_name, period, value, unit, source_type, source_url
        """
        records = []
        result = raw_data.get("result", {})
        data = result.get("data", {})
        series_results = data.get("series_results", [])

        for item in series_results:
            indicator_name = item.get("indicator_name", "")
            if not indicator_name:
                continue

            # value 转为 float（如果可以）
            value = item.get("value")
            try:
                value = float(value) if value is not None else None
            except (ValueError, TypeError):
                value = None

            records.append({
                "indicator_name": indicator_name,
                "period": item.get("period"),
                "value": value,
                "unit": item.get("unit"),
                "source_type": item.get("source_type", "stats_gov_release"),
                "source_url": item.get("source_url"),
                "fetched_at": raw_data.get("meta", {}).get("fetch_time"),
            })

        return records

    def build_staging_payload(self, records: list[dict]) -> dict:
        """
        构建 staging payload
        宏观 staging 格式与接口格式一致，是 records 数组
        """
        return {
            "generated_at": self._now_iso(),
            "records": records,
        }

    def write_staging(self, records: list[dict], staging_path: Path) -> int:
        """写入 staging 文件（宏观格式特殊：顶层是 records 不是 payload）"""
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_obj = {
            "generated_at": self._now_iso(),
            "records": records,
        }
        staging_path.write_text(json.dumps(staging_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(records)

    def build_manifest(self, job_id: str, staging_path: Path, staging_count: int,
                       checksum: str, begin_date: str | None, end_date: str | None) -> dict:
        """宏观 manifest 略有不同：staging 顶层是 records 不是 payload"""
        raw_rel = str(staging_path).replace(str(self.backend_root) + "/", "")
        return {
            "spec_version": self.SPEC_VERSION,
            "staging_format_version": "1.0",
            "job_id": job_id,
            "created_at": self._now_iso(),
            "producer": {
                "system": "openclaw",
                "module": self.__class__.__name__,
                "run_id": job_id,
            },
            "data_category": self.DATA_CATEGORY,
            "time_window": {
                "begin_date": begin_date,
                "end_date": end_date,
            },
            "target": {
                "endpoint": self.TARGET_ENDPOINT,
                "ingest_package": self.INGEST_PACKAGE,
                "ingest_field": self.INGEST_FIELD,
                "target_table": self.TARGET_TABLE,
            },
            "files": {
                "staging_path": raw_rel,
            },
            "record_stats": {
                "staging_count": staging_count,
                "expected_write_count": staging_count,
            },
            "checksum": {
                "staging_sha256": checksum,
            },
            "status": "ready",
        }

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _now_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
