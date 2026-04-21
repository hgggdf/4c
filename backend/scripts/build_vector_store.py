"""兼容旧脚本路径，转发到 legacy.scripts.build_vector_store。"""

from legacy.scripts.build_vector_store import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(LEGACY_SCRIPT_MESSAGE)