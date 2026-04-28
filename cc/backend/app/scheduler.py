"""每日定时同步：SSH 隧道下载 + 批量入库。"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from apscheduler.schedulers.background import BackgroundScheduler

from config import get_settings

logger = logging.getLogger("scheduler")

DIRS = {
    "company": "company_records.jsonl",
    "financial": "financial_records.jsonl",
    "announcement": "announcement_records.jsonl",
    "research_report": "research_report_records.jsonl",
    "news": "news_records.jsonl",
    "macro": "macro_records.jsonl",
}

REMOTE_BASE_URL = "data/incoming/today"

_scheduler: BackgroundScheduler | None = None


def _download_file(port: int, relative_url: str, local_path: str) -> bool:
    full_url = f"http://localhost:{port}/{relative_url}"
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        resp = requests.get(full_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("下载完成: %s -> %s", relative_url, local_path)
        return True
    except Exception as e:
        logger.error("下载失败: %s  原因: %s", relative_url, e)
        return False


def _download_all(port: int, save_root: Path) -> bool:
    today_dir = save_root / "today"
    today_dir.mkdir(parents=True, exist_ok=True)

    _download_file(port, f"{REMOTE_BASE_URL}/manifest.json",
                   str(today_dir / "manifest.json"))

    for dir_name, jsonl_name in DIRS.items():
        jsonl_url = f"{REMOTE_BASE_URL}/{dir_name}/{jsonl_name}"
        jsonl_local = today_dir / dir_name / jsonl_name
        _download_file(port, jsonl_url, str(jsonl_local))

        if not jsonl_local.exists():
            logger.info("%s 无数据文件，跳过附件下载", dir_name)
            continue

        with open(jsonl_local, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("local_file"):
                    file_url = f"{REMOTE_BASE_URL}/{dir_name}/{rec['local_file']}"
                    file_local = str(today_dir / dir_name / rec["local_file"])
                    _download_file(port, file_url, file_local)

    return (today_dir / "manifest.json").exists()


def daily_sync_job():
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent
    save_root = backend_dir / "data" / "incoming"

    ssh_cmd = [
        "ssh", "-L",
        f"{settings.sync_ssh_local_port}:localhost:{settings.sync_ssh_remote_port}",
        f"{settings.sync_ssh_user}@{settings.sync_ssh_host}",
        "-N", "-o", "StrictHostKeyChecking=no",
    ]

    logger.info("===== 每日同步开始 [%s] =====", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    tunnel = None
    try:
        tunnel = subprocess.Popen(ssh_cmd)
        time.sleep(3)

        ok = _download_all(settings.sync_ssh_local_port, save_root)
        if not ok:
            logger.error("下载阶段失败，跳过入库")
            return

        import import_batch
        batch_dir = save_root / "today"
        if not (batch_dir / "manifest.json").exists():
            logger.warning("manifest.json 不存在，跳过入库")
            return

        original_cwd = os.getcwd()
        os.chdir(str(backend_dir))
        try:
            success = import_batch.process_batch(batch_dir)
            if success:
                logger.info("入库完成")
            else:
                logger.warning("入库部分失败，请检查 data/failed/ 目录")
        finally:
            os.chdir(original_cwd)

        # 入库后执行冷热交替
        try:
            from app.core.database.session import SessionLocal
            from ingest_center.hot_archive_service import HotArchiveService
            with SessionLocal() as db:
                svc = HotArchiveService(db)
                archived = svc.archive_cold(dry_run=False)
                logger.info("冷热交替完成，转冷 %s 条", archived)
                if datetime.now().day == 1:
                    result = svc.decay_query_counts()
                    logger.info("query_count 衰减完成: %s", result)
        except Exception as e:
            logger.error("冷热交替异常: %s", e, exc_info=True)

    except Exception as e:
        logger.error("每日同步异常: %s", e, exc_info=True)
    finally:
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=5)
            logger.info("SSH 隧道已关闭")

    logger.info("===== 每日同步结束 =====")


def start_scheduler():
    global _scheduler
    settings = get_settings()

    if not settings.sync_enabled:
        logger.info("定时同步已禁用 (sync_enabled=false)")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        daily_sync_job,
        trigger="cron",
        hour=settings.sync_hour,
        minute=settings.sync_minute,
        id="daily_sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("定时同步已启动，每天 %02d:%02d 执行", settings.sync_hour, settings.sync_minute)
