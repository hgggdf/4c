"""兼容旧脚本路径，转发到 legacy.scripts.test_retrieval。"""

from legacy.scripts.test_retrieval import *  # noqa: F401,F403

if __name__ == "__main__":
    run_tests()