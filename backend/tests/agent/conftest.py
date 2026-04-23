"""Agent测试 fixtures - 使用独立的测试数据库配置"""

import sys
from pathlib import Path

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 在导入任何 app 模块之前，先 mock 掉会触发 MySQL 连接的模块
import pytest
from unittest.mock import MagicMock

# Mock app.core.database.session 避免触发 MySQL 连接
sys.modules['app.core.database.session'] = MagicMock()

# 现在可以安全导入了
from tests.service.conftest import (  # noqa: F401, E402
    engine,
    session_factory,
    services,
)
