"""外部大模型客户端实现。

Some providers are optional at runtime. Import them lazily so the backend can
start even when a specific SDK is not installed.
"""

from .glm_client import GLMClient

try:
    from .claude_client import ClaudeClient
except ModuleNotFoundError:  # optional dependency
    ClaudeClient = None  # type: ignore[assignment]

try:
    from .kimi_client import KimiClient
except ModuleNotFoundError:  # optional dependency
    KimiClient = None  # type: ignore[assignment]

__all__ = ["GLMClient", "ClaudeClient", "KimiClient"]