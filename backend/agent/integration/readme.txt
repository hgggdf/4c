文件夹说明：backend/agent/integration/
====================
本文件夹为智能体集成模块，包含多种代理实现、实体解析、工具调度等核心逻辑。

文件说明：
- agent.py：基础代理类定义。
- clarification_detector.py：澄清意图检测器，判断用户是否需要进一步说明。
- entity_resolver.py：实体解析器，识别用户输入中的公司、股票等实体。
- followup_generator.py：后续问题生成器，生成推荐的追问。
- freshness_router.py：时效性路由器，根据数据新鲜度选择数据源。
- glm_agent.py：GLM 模型代理实现。
- langgraph_agent.py：基于 LangGraph 的代理实现。
- medical_adapter.py：医药领域适配器。
- medical_analyzer.py：医药数据分析器。
- mode_resolver.py：模式解析器，判断用户意图对应的工作模式。
- output_builder.py：输出构建器，格式化代理的回复内容。
- preference_profiler.py：用户偏好分析器。
- react_agent.py：ReAct 模式代理实现。
- serialization.py：序列化工具。
- state.py：代理状态管理。
- tool_executor.py：工具执行器，调度和执行各类工具。
- tool_planner.py：工具规划器，规划工具调用顺序。
