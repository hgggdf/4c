"""
ingest_center / manifest_model.py
================================

Manifest 结构相关模块。

职责：
    定义 manifest 的数据模型、解析函数与序列化函数。
    manifest 由 OpenClaw 产出，格式必须与 OpenClaw 对接契约严格一致。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class TimeWindow:
    """数据时间窗口。"""
    begin_date: str
    end_date: str


@dataclass
class Producer:
    """产生方标识。"""
    system: str
    module: str
    run_id: str


@dataclass
class Target:
    """入库目标描述。

    字段说明：
        endpoint        — 后端入库接口路径
        ingest_package  — 接口对应的 package 标识
        ingest_field    — 目标字段/映射标识
        target_table    — 最终写入的目标表名
    """
    endpoint: str
    ingest_package: str
    ingest_field: str
    target_table: str


@dataclass
class Files:
    """一次任务产出的文件路径集合。

    字段说明：
        raw_path            — raw 数据路径（辅助追溯）
        staging_path        — staging 数据路径（入库程序直接消费）
        quality_report_path — 质量报告路径（辅助追溯）
    """
    raw_path: str
    staging_path: str
    quality_report_path: str


@dataclass
class RecordStats:
    """记录统计信息。"""
    raw_count: int
    staging_count: int
    expected_write_count: int


@dataclass
class Checksum:
    """校验信息。"""
    staging_sha256: str


@dataclass
class Manifest:
    """OpenClaw 产出的 manifest 结构化表示。"""
    spec_version: str
    job_id: str
    created_at: str
    producer: Producer
    data_category: str
    time_window: TimeWindow
    target: Target
    files: Files
    record_stats: RecordStats
    checksum: Checksum
    status: str = "ready"


def _build_manifest(raw: Dict[str, Any]) -> Manifest:
    """从原始字典构建 Manifest 实例。"""
    return Manifest(
        spec_version=raw["spec_version"],
        job_id=raw["job_id"],
        created_at=raw["created_at"],
        producer=Producer(
            system=raw["producer"]["system"],
            module=raw["producer"]["module"],
            run_id=raw["producer"]["run_id"],
        ),
        data_category=raw["data_category"],
        time_window=TimeWindow(
            begin_date=raw["time_window"]["begin_date"],
            end_date=raw["time_window"]["end_date"],
        ),
        target=Target(
            endpoint=raw["target"]["endpoint"],
            ingest_package=raw["target"]["ingest_package"],
            ingest_field=raw["target"]["ingest_field"],
            target_table=raw["target"]["target_table"],
        ),
        files=Files(
            raw_path=raw["files"]["raw_path"],
            staging_path=raw["files"]["staging_path"],
            quality_report_path=raw["files"]["quality_report_path"],
        ),
        record_stats=RecordStats(
            raw_count=raw["record_stats"]["raw_count"],
            staging_count=raw["record_stats"]["staging_count"],
            expected_write_count=raw["record_stats"]["expected_write_count"],
        ),
        checksum=Checksum(
            staging_sha256=raw["checksum"]["staging_sha256"],
        ),
        status=raw.get("status", "ready"),
    )


def _assert_field_present(container: Dict[str, Any], field: str, prefix: str = "") -> None:
    """辅助函数：检查字段存在，否则抛出 ValueError。"""
    if field not in container:
        raise ValueError(f"manifest missing required field: {prefix}{field}")


def parse_manifest(json_path: str) -> Manifest:
    """
    从 JSON 文件路径解析 manifest，并做显式字段存在校验。

    Args:
        json_path: manifest 文件的绝对或相对路径。

    Returns:
        解析后的 Manifest 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 缺少必要字段。
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 顶层字段校验
    required_top = [
        "spec_version", "job_id", "created_at", "producer",
        "data_category", "time_window", "target", "files",
        "record_stats", "checksum", "status",
    ]
    for key in required_top:
        _assert_field_present(raw, key)

    # producer 子字段校验
    producer = raw["producer"]
    for key in ("system", "module", "run_id"):
        _assert_field_present(producer, key, prefix="producer.")

    # time_window 子字段校验
    time_window = raw["time_window"]
    for key in ("begin_date", "end_date"):
        _assert_field_present(time_window, key, prefix="time_window.")

    # target 子字段校验
    target = raw["target"]
    for key in ("endpoint", "ingest_package", "ingest_field", "target_table"):
        _assert_field_present(target, key, prefix="target.")

    # files 子字段校验
    files = raw["files"]
    for key in ("raw_path", "staging_path", "quality_report_path"):
        _assert_field_present(files, key, prefix="files.")

    # record_stats 子字段校验
    record_stats = raw["record_stats"]
    for key in ("raw_count", "staging_count", "expected_write_count"):
        _assert_field_present(record_stats, key, prefix="record_stats.")

    # checksum 子字段校验
    checksum = raw["checksum"]
    for key in ("staging_sha256",):
        _assert_field_present(checksum, key, prefix="checksum.")

    return _build_manifest(raw)


def manifest_to_dict(manifest: Manifest) -> Dict[str, Any]:
    """
    将 Manifest 实例序列化为字典。

    Args:
        manifest: Manifest 实例。

    Returns:
        符合 OpenClaw 规范的字典。
    """
    return asdict(manifest)
