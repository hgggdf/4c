# 4C医药投资分析系统 - Agent工具包与提示词集合

## 项目概述

本项目为4C医药投资分析系统实现了完整的Agent工具函数包和提示词模板集合，使得后期数据接入Agent后可以直接运行，无需额外开发。

## 目录结构

```
backend/
├── agent/
│   ├── tools/                      # 工具函数包
│   │   ├── __init__.py            # 工具导出
│   │   ├── company_tools.py       # 公司信息查询工具
│   │   ├── financial_tools.py     # 财务数据查询工具
│   │   ├── announcement_tools.py  # 公告事件查询工具
│   │   ├── news_tools.py          # 新闻舆情查询工具
│   │   ├── macro_tools.py         # 宏观指标查询工具
│   │   ├── retrieval_tools.py     # 向量检索工具
│   │   └── registry.py            # 工具注册表
│   ├── prompts/                    # 提示词模板
│   │   ├── __init__.py            # 提示词导出
│   │   ├── system_prompt.py       # 系统提示词
│   │   ├── chat_prompt.py         # 对话提示词构建
│   │   └── templates.py           # 提示词模板集合
│   ├── integration/                # Agent集成
│   │   ├── glm_agent.py           # GLM Agent实现
│   │   └── agent.py               # Agent基类
│   ├── llm_clients/                # LLM客户端
│   │   └── glm_client.py          # GLM API客户端
│   ├── __init__.py                # Agent包导出
│   └── README.md                  # 使用文档
├── examples/                       # 示例代码
│   ├── tool_examples.py           # 工具函数使用示例
│   ├── prompt_examples.py         # 提示词模板使用示例
│   └── agent_examples.py          # Agent集成示例
└── app/
    └── service/                    # 服务层（数据库接口）
        ├── company_service.py      # 公司信息服务
        ├── financial_service.py    # 财务数据服务
        ├── announcement_service.py # 公告事件服务
        ├── news_service.py         # 新闻舆情服务
        ├── macro_service.py        # 宏观指标服务
        └── retrieval_service.py    # 向量检索服务
```

## 核心功能

### 1. 工具函数包 (agent/tools/)

封装了所有数据库接口为Agent可调用的工具函数，共6大类：

#### 1.1 公司信息工具 (company_tools.py)
- `get_company_basic_info(stock_code)` - 获取公司基本信息
- `get_company_profile(stock_code)` - 获取公司详细资料
- `get_company_overview(stock_code)` - 获取公司完整概览
- `resolve_company_from_text(text)` - 从文本识别公司

#### 1.2 财务数据工具 (financial_tools.py)
- `get_income_statements(stock_code, limit)` - 获取利润表
- `get_balance_sheets(stock_code, limit)` - 获取资产负债表
- `get_cashflow_statements(stock_code, limit)` - 获取现金流量表
- `get_financial_metrics(stock_code, metric_names, limit)` - 获取财务指标
- `get_business_segments(stock_code, limit)` - 获取业务分部
- `get_financial_summary(stock_code, period_count)` - 获取财务汇总

#### 1.3 公告事件工具 (announcement_tools.py)
- `get_raw_announcements(stock_code, days)` - 获取原始公告
- `get_structured_announcements(stock_code, days, category)` - 获取结构化公告
- `get_drug_approvals(stock_code, days)` - 获取药品批准事件
- `get_clinical_trials(stock_code, days)` - 获取临床试验事件
- `get_procurement_events(stock_code, days)` - 获取集采中标事件
- `get_regulatory_risks(stock_code, days)` - 获取监管风险事件
- `get_company_event_summary(stock_code, days)` - 获取公司事件汇总

#### 1.4 新闻舆情工具 (news_tools.py)
- `get_news_raw(days, news_type)` - 获取原始新闻
- `get_news_by_company(stock_code, days)` - 获取公司相关新闻
- `get_news_by_industry(industry_code, days)` - 获取行业新闻
- `get_company_news_impact(stock_code, days)` - 获取公司新闻影响分析
- `get_industry_news_impact(industry_code, days)` - 获取行业新闻影响分析

#### 1.5 宏观指标工具 (macro_tools.py)
- `get_macro_indicator(indicator_name, period)` - 获取单个宏观指标
- `list_macro_indicators(indicator_names, periods)` - 批量获取宏观指标
- `get_macro_summary(indicator_names, recent_n)` - 获取宏观指标汇总

#### 1.6 向量检索工具 (retrieval_tools.py)
- `search_documents(query, stock_code, industry_code, doc_types, top_k)` - 全库语义检索
- `search_company_evidence(query, stock_code, top_k)` - 检索公司证据
- `search_news_evidence(query, stock_code, industry_code, top_k)` - 检索新闻证据

### 2. 提示词模板集合 (agent/prompts/templates.py)

提供了7种分析场景的结构化提示词模板：

#### 2.1 系统提示词
- `SYSTEM_BASE` - 基础系统提示词，定义Agent能力和回答原则

#### 2.2 分析场景模板
- `COMPANY_ANALYSIS` - 公司全面分析（6个维度：概况、财务、管线、政策、舆情、建议）
- `FINANCIAL_ANALYSIS` - 财务深度分析（6个维度：盈利、成长、现金流、资产、研发、风险）
- `DRUG_PIPELINE_ANALYSIS` - 药品管线分析（6个维度：上市产品、在研管线、进展、技术、竞争、价值）
- `POLICY_IMPACT_ANALYSIS` - 政策影响分析（6个维度：集采、医保、DRG、其他政策、趋势、应对）
- `INDUSTRY_COMPARISON` - 行业对比分析（6个维度：财务、估值、业务、政策、风险、评分）
- `RISK_WARNING` - 风险预警分析（6类风险：财务、经营、政策、法律、市场、其他）
- `QUICK_QUERY` - 快速查询（简明回答，300字以内）

#### 2.3 提示词构建方法
- `build_company_analysis_prompt(stock_code, stock_name)` - 构建公司分析提示词
- `build_financial_analysis_prompt(stock_code, stock_name)` - 构建财务分析提示词
- `build_drug_pipeline_prompt(stock_code, stock_name)` - 构建管线分析提示词
- `build_policy_impact_prompt(stock_code, stock_name)` - 构建政策影响提示词
- `build_industry_comparison_prompt(stock_code, stock_name)` - 构建行业对比提示词
- `build_risk_warning_prompt(stock_code, stock_name)` - 构建风险预警提示词
- `build_quick_query_prompt(query)` - 构建快速查询提示词

### 3. Agent集成 (agent/integration/)

#### 3.1 GLMMinimalAgent
- 基于智谱GLM API的最小化Agent实现
- 支持股票上下文解析、分析摘要构建、图表上下文、证据收集
- 内置缓存机制，提升响应速度
- 支持对话历史

#### 3.2 LangChainAgentStub
- LangChain Agent包装器（占位实现）
- 可扩展为完整的LangChain Agent

### 4. 示例代码 (examples/)

#### 4.1 工具函数示例 (tool_examples.py)
- 公司信息工具使用示例
- 财务数据工具使用示例
- 公告事件工具使用示例
- 新闻舆情工具使用示例
- 宏观指标工具使用示例
- 向量检索工具使用示例

#### 4.2 提示词模板示例 (prompt_examples.py)
- 系统提示词示例
- 各类分析场景提示词示例
- 自定义模板示例

#### 4.3 Agent集成示例 (agent_examples.py)
- GLMMinimalAgent使用示例
- 自定义Agent实现示例
- 流式输出Agent示例
- 批量分析Agent示例
- 多策略Agent示例

## 快速开始

### 1. 导入工具函数

```python
from agent import (
    # 公司信息
    get_company_overview,
    # 财务数据
    get_financial_summary,
    # 公告事件
    get_company_event_summary,
    # 新闻舆情
    get_company_news_impact,
    # 向量检索
    search_company_evidence,
)

# 获取公司完整信息
overview = get_company_overview("600276")
print(f"公司: {overview['stock_name']}")

# 获取财务汇总
financial = get_financial_summary("600276", period_count=4)
print(f"营业收入: {financial['latest_income']['revenue']}")
```

### 2. 使用提示词模板

```python
from agent import PromptTemplates

# 构建公司分析提示词
prompt = PromptTemplates.build_company_analysis_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 提示词包含完整的分析框架和数据获取步骤
print(prompt)
```

### 3. 使用Agent

```python
from agent import GLMMinimalAgent

# 初始化Agent
agent = GLMMinimalAgent()

# 运行查询
result = agent.run(
    message="分析恒瑞医药的研发管线",
    targets=[{"type": "stock", "symbol": "600276"}],
    current_stock_code="600276",
    user_id=1,
    session_id=1001
)

# 获取结果
print(f"回答: {result['answer']}")
print(f"建议: {result['suggestion']}")
```

## 技术特点

### 1. 框架无关设计
- 工具函数不依赖特定Agent框架
- 可轻松集成到LangChain、LlamaIndex、AutoGPT等框架
- 支持自定义Agent实现

### 2. 完整的错误处理
- 所有工具函数都有完善的错误处理
- 返回统一的ServiceResult格式
- 提供清晰的错误信息

### 3. 高性能优化
- 内置缓存机制
- 支持批量查询
- 向量检索加速

### 4. 丰富的文档和示例
- 详细的API文档
- 完整的使用示例
- 最佳实践指南

## 数据覆盖

### 公司数据
- 基本信息：股票代码、名称、行业、上市日期
- 详细资料：业务概述、核心产品、市场地位
- 行业分类：多级行业分类体系

### 财务数据
- 三大报表：利润表、资产负债表、现金流量表
- 财务指标：ROE、毛利率、净利率、研发费用率等
- 业务分部：按产品/地区的收入结构

### 公告事件
- 原始公告：完整公告内容
- 结构化公告：分类、摘要、信号类型
- 药品批准：新药批准、适应症、创新药标识
- 临床试验：试验阶段、进展情况
- 集采事件：中标结果、价格变化
- 监管风险：处罚、警告、调查

### 新闻舆情
- 原始新闻：标题、内容、来源
- 公司新闻：影响方向、影响强度
- 行业新闻：行业级影响分析
- 舆情分析：情感倾向、影响评估

### 宏观数据
- 经济指标：GDP、CPI、PPI、PMI等
- 时间序列：支持多期数据查询

### 向量检索
- 语义检索：基于ChromaDB的向量检索
- 多文档类型：公告、财务附注、新闻、研报
- 智能过滤：按公司、行业、文档类型过滤

## 应用场景

### 1. 投资研究
- 公司基本面分析
- 财务健康度评估
- 研发管线评估
- 政策影响分析

### 2. 风险管理
- 财务风险预警
- 监管风险识别
- 舆情风险监控

### 3. 行业研究
- 行业对比分析
- 竞争格局分析
- 政策趋势研究

### 4. 智能问答
- 快速查询
- 深度分析
- 报告生成

## 扩展性

### 1. 添加新工具函数
在对应的工具文件中添加新函数，并在`__init__.py`中导出：

```python
# agent/tools/custom_tools.py
def custom_analysis(stock_code: str) -> dict:
    """自定义分析工具"""
    # 实现逻辑
    pass

# agent/tools/__init__.py
from .custom_tools import custom_analysis
__all__ = [..., "custom_analysis"]
```

### 2. 添加新提示词模板
在`templates.py`中添加新模板：

```python
class PromptTemplates:
    CUSTOM_ANALYSIS = """
    # 自定义分析模板
    ...
    """
    
    @staticmethod
    def build_custom_analysis_prompt(**kwargs):
        return PromptTemplates.format_template(
            PromptTemplates.CUSTOM_ANALYSIS,
            **kwargs
        )
```

### 3. 实现自定义Agent
继承或组合现有Agent实现：

```python
from agent import GLMMinimalAgent
from agent.tools import get_company_overview

class CustomAgent(GLMMinimalAgent):
    def custom_method(self, stock_code: str):
        # 自定义逻辑
        pass
```

## 性能优化建议

### 1. 使用缓存
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_get_financial_summary(stock_code: str):
    return get_financial_summary(stock_code)
```

### 2. 批量查询
```python
stock_codes = ["600276", "000661", "002821"]
results = [get_company_overview(code) for code in stock_codes]
```

### 3. 限制返回数据量
```python
# 只获取最近2期数据
financial = get_financial_summary(stock_code, period_count=2)
```

### 4. 使用汇总接口
```python
# 优先使用汇总接口，减少多次查询
summary = get_financial_summary(stock_code)  # 一次获取所有财务数据
```

## 注意事项

1. **数据库连接**：所有工具函数需要数据库连接才能运行
2. **股票代码格式**：使用6位数字格式，如"600519"
3. **日期范围**：days参数表示查询最近N天的数据
4. **错误处理**：建议使用try-except捕获异常
5. **LLM配置**：GLMMinimalAgent需要配置GLM API密钥

## 后续计划

- [ ] 支持更多LLM（OpenAI、Claude等）
- [ ] 添加更多分析场景模板
- [ ] 实现Agent工作流编排
- [ ] 添加可视化图表生成
- [ ] 支持多语言（中英文）
- [ ] 添加单元测试

## 技术支持

如有问题或建议，请联系开发团队。

---

**版本**: 1.0.0  
**更新日期**: 2026-04-22  
**作者**: 4C开发团队
