"""兼容旧脚本路径，转发到 legacy.scripts.import_financial_data。"""

from legacy.scripts.import_financial_data import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(LEGACY_SCRIPT_MESSAGE)