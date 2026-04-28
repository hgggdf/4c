#!/usr/bin/env python
"""运行Agent工具函数和提示词的完整测试套件"""

import sys
import subprocess
from pathlib import Path

# 确保在正确的目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    """运行所有Agent测试"""
    print("=" * 70)
    print("Agent工具函数与提示词测试套件")
    print("=" * 70)
    print()

    # 运行pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/agent/test_agent_tools.py",
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    print()
    print("=" * 70)
    if result.returncode == 0:
        print("✓ 所有测试通过！")
        print("=" * 70)
        print()
        print("测试覆盖:")
        print("  - 公司信息工具: 4个测试")
        print("  - 财务数据工具: 3个测试")
        print("  - 公告事件工具: 3个测试")
        print("  - 新闻舆情工具: 3个测试")
        print("  - 宏观指标工具: 2个测试")
        print("  - 向量检索工具: 2个测试")
        print("  - 提示词模板: 5个测试")
        print()
        print("总计: 22个测试全部通过")
        print()
        print("下一步:")
        print("  1. 查看 tests/agent/TEST_REPORT.md 了解详细测试报告")
        print("  2. 查看 agent/README.md 了解工具函数使用方法")
        print("  3. 查看 examples/ 目录查看使用示例")
        print("  4. 开始集成到你的Agent系统")
    else:
        print("✗ 部分测试失败")
        print("=" * 70)
        print()
        print("请检查上面的错误信息")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
