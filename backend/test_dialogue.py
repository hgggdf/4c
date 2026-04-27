"""测试 DialogueAgent 和 KimiClient 的流式对话功能"""

import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from agent.dialogue_agent import DialogueAgent


def test_chat_stream():
    """测试流式对话"""
    agent = DialogueAgent()

    # 检查配置
    if not agent.is_configured():
        print("❌ Kimi API 未配置")
        print("请在 backend/.env 中设置:")
        print("  KIMI_API_KEY=your_key")
        print("  KIMI_BASE_URL=https://api.moonshot.ai/v1")
        print("  KIMI_MODEL=moonshot-v1-8k")
        return

    print("✓ Kimi API 已配置")
    print(f"  Base URL: {agent.llm_client.base_url}")
    print(f"  Model: {agent.llm_client.model}")
    print()

    # 测试简单问答
    question = "你好，请用一句话介绍你自己"
    print(f"问题: {question}")
    print("回答: ", end="", flush=True)

    try:
        for chunk in agent.chat_stream(question):
            print(chunk, end="", flush=True)
        print("\n")
        print("✓ 流式对话测试成功")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_history():
    """测试带历史记录的对话"""
    agent = DialogueAgent()

    if not agent.is_configured():
        print("❌ Kimi API 未配置")
        return

    print("\n--- 测试多轮对话 ---")

    history = [
        {"role": "user", "content": "我想了解贵州茅台"},
        {"role": "assistant", "content": "贵州茅台是中国知名白酒品牌，股票代码 600519"}
    ]

    question = "它的股价表现如何？"
    print(f"历史: {len(history)} 条消息")
    print(f"问题: {question}")
    print("回答: ", end="", flush=True)

    try:
        for chunk in agent.chat_stream(question, history=history):
            print(chunk, end="", flush=True)
        print("\n")
        print("✓ 多轮对话测试成功")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    print("=== DialogueAgent 业务层测试 ===\n")
    test_chat_stream()
    test_with_history()
