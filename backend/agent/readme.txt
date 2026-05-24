文件夹说明：backend/agent/
====================
本文件夹为 AI 智能体系统模块，负责对话管理、蝴蝶分析、会话记忆等智能交互功能。

文件说明：
- butterfly_analyzer.py：蝴蝶效应分析器，用于金融事件的连锁影响分析。
- dialogue_agent.py：对话代理，管理用户与 AI 的多轮对话。
- session_memory.py：会话记忆管理，维护对话上下文。

子文件夹说明：
- integration/：智能体集成模块，包含各类代理实现和工具调度。
- llm_clients/：大语言模型客户端，对接不同 LLM 服务。
- prompts/：提示词模板，定义系统提示和对话模板。
- tools/：智能体工具集，提供金融数据查询、分析等能力。
