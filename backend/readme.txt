文件夹说明：backend/
====================
本文件夹为项目的 Python 后端服务，基于 FastAPI 框架构建，提供金融数据分析、AI 智能体对话、数据爬取与入库等核心功能。

文件说明：
- main.py：应用程序入口，启动 FastAPI 服务。
- config.py：全局配置文件，包含数据库连接、API 密钥等配置项。
- requirements.txt：Python 依赖包列表。
- import_batch.py：批量数据导入脚本。
- restore_data.py：数据恢复脚本。
- tunnel_download.py：隧道下载工具。
- knowledge_store.json：知识库配置文件。

子文件夹说明：
- agent/：AI 智能体系统，包含对话代理、分析器、LLM 客户端等。
- app/：主应用模块，包含数据库、路由、服务层、仓储层等核心代码。
- crawler/：数据爬取与转换模块。
- chroma_db/：Chroma 向量数据库存储目录。
- data/：数据存储目录（incoming/processed）。
- examples/：示例脚本。
- ingest_center/：数据入库中心。
- scripts/：运维与数据处理脚本。
