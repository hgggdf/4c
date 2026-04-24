"""
ingest_center / config.py
========================

基础配置常量占位模块。

职责：
    集中管理入库程序运行所需的常量与路径，例如：
    - manifest 与 staging 的根目录
    - 目标后端 API 基地址
    - 默认超时、重试次数
    - 各 data_category 的开关或白名单

注意：
    manifest 中的 target.endpoint 由 OpenClaw 根据 data_category 写入，
    实际入库时应与 dispatcher.CATEGORY_ENDPOINT_MAP 保持一致。
"""

import os

# 项目根目录（backend/ 的上级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 存放待处理 manifest 的目录（可存放 OpenClaw 投递过来的 json 文件）
MANIFEST_DIR = os.path.join(os.path.dirname(__file__), "manifests")

# 入库完成后生成的回执/日志目录
RECEIPT_DIR = os.path.join(os.path.dirname(__file__), "receipts")

# 目标后端 API 基地址（入库程序通过 HTTP 调用现有接口）
API_BASE_URL = os.environ.get("INGEST_API_BASE_URL", "http://127.0.0.1:8000")

# 默认请求超时（秒）
DEFAULT_TIMEOUT = 30

# 默认重试次数
DEFAULT_RETRIES = 3

# data_category 白名单：当前允许入库的类别
# 注意：patent 只允许 raw/staging，不允许入库，因此不在白名单中
ALLOWED_CATEGORIES = {
    "company",
    "stock_daily",
    "announcement_raw",
    "research_report",
    "macro",
    "financial_package",
}

# 仅做 staging 校验但强制 skip 入库的类别
SKIP_INGEST_CATEGORIES = {
    "patent",
}
