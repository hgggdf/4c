# Agent工具函数与提示词使用指南

本文档介绍如何使用Agent工具函数包和提示词模板集合，实现医药投资分析Agent的快速开发。

## 目录

1. [快速开始](#快速开始)
2. [工具函数使用](#工具函数使用)
3. [提示词模板使用](#提示词模板使用)
4. [Agent集成示例](#agent集成示例)
5. [最佳实践](#最佳实践)

---

## 快速开始

### 安装依赖

确保已安装项目依赖：

```bash
cd C:\Users\chenyichang\Desktop\4c\backend
pip install -r requirements.txt
```

### 基本导入

```python
from agent import (
    # 工具函数
    get_company_overview,
    get_financial_summary,
    get_company_event_summary,
    search_company_evidence,
    # 提示词模板
    PromptTemplates,
    # Agent实现
    GLMMinimalAgent,
)
```

---

## 工具函数使用

### 1. 公司信息查询

#### 获取公司基本信息

```python
from agent import get_company_basic_info

# 获取贵州茅台基本信息
company_info = get_company_basic_info("600519")
print(f"公司名称: {company_info['stock_name']}")
print(f"所属行业: {company_info['industry_level1']} - {company_info['industry_level2']}")
print(f"上市日期: {company_info['listing_date']}")
```

#### 获取公司完整概览

```python
from agent import get_company_overview

# 获取恒瑞医药完整信息
overview = get_company_overview("600276")
print(f"业务概述: {overview['profile']['business_summary']}")
print(f"核心产品: {overview['profile']['core_products_json']}")
print(f"行业分类: {[ind['industry_name'] for ind in overview['industries']]}")
```

#### 从文本识别公司

```python
from agent import resolve_company_from_text

# 从用户输入识别公司
companies = resolve_company_from_text("恒瑞医药")
if companies:
    stock_code = companies[0]['stock_code']
    stock_name = companies[0]['stock_name']
    print(f"识别到公司: {stock_name} ({stock_code})")
```

### 2. 财务数据查询

#### 获取财务汇总

```python
from agent import get_financial_summary

# 获取最近4期财务数据
financial = get_financial_summary("600276", period_count=4)

# 最新一期利润表
latest_income = financial['latest_income']
print(f"营业收入: {latest_income['revenue']}")
print(f"净利润: {latest_income['net_profit']}")
print(f"研发费用: {latest_income['rd_expense']}")

# 关键指标
for metric in financial['key_metrics']:
    print(f"{metric['metric_name']}: {metric['metric_value']}{metric['metric_unit']}")
```

#### 获取特定财务指标

```python
from agent import get_financial_metrics

# 获取ROE、毛利率、研发费用率
metrics = get_financial_metrics(
    stock_code="600276",
    metric_names=["roe", "gross_margin", "rd_ratio"],
    limit=4
)

for metric in metrics:
    print(f"{metric['report_date']} {metric['metric_name']}: {metric['metric_value']}")
```

### 3. 公告事件查询

#### 获取药品批准事件

```python
from agent import get_drug_approvals

# 获取最近1年的药品批准
approvals = get_drug_approvals("600276", days=365)

for approval in approvals:
    print(f"药品: {approval['drug_name']}")
    print(f"批准类型: {approval['approval_type']}")
    print(f"适应症: {approval['indication']}")
    print(f"是否创新药: {approval['is_innovative_drug']}")
    print("---")
```

#### 获取集采中标事件

```python
from agent import get_procurement_events

# 获取集采中标情况
procurements = get_procurement_events("600276", days=365)

for proc in procurements:
    print(f"药品: {proc['drug_name']}")
    print(f"集采轮次: {proc['procurement_round']}")
    print(f"中标结果: {proc['bid_result']}")
    print(f"价格变化: {proc['price_change_ratio']}")
    print("---")
```

#### 获取公司事件汇总

```python
from agent import get_company_event_summary

# 获取所有类型的事件汇总
events = get_company_event_summary("600276", days=365)

print(f"结构化公告数: {len(events['structured_announcements'])}")
print(f"药品批准数: {len(events['drug_approvals'])}")
print(f"临床试验数: {len(events['clinical_trials'])}")
print(f"集采事件数: {len(events['procurement_events'])}")
print(f"监管风险数: {len(events['regulatory_risks'])}")

# 按信号类型分类
print(f"机会类公告: {len(events['opportunity_items'])}")
print(f"风险类公告: {len(events['risk_items'])}")
```

### 4. 新闻舆情查询

#### 获取公司新闻影响

```python
from agent import get_company_news_impact

# 获取最近90天的新闻影响分析
news_impact = get_company_news_impact("600276", days=90)

print(f"新闻总数: {len(news_impact['items'])}")
print(f"影响方向统计: {news_impact['direction_counts']}")
print(f"平均影响强度: {news_impact['avg_impact_strength']}")

# 查看具体新闻
for news in news_impact['items'][:5]:
    print(f"标题: {news['title']}")
    print(f"影响方向: {news['impact_direction']}")
    print(f"影响强度: {news['impact_strength']}")
    print("---")
```

#### 获取行业新闻影响

```python
from agent import get_industry_news_impact

# 获取医药制造行业新闻
industry_news = get_industry_news_impact("C27", days=30)

print(f"行业新闻数: {len(industry_news['items'])}")
print(f"影响方向统计: {industry_news['direction_counts']}")
```

### 5. 宏观指标查询

#### 获取宏观指标汇总

```python
from agent import get_macro_summary

# 获取关键宏观指标的最近6期数据
macro = get_macro_summary(
    indicator_names=["GDP增速", "CPI", "PMI", "社会融资规模"],
    recent_n=6
)

for indicator_name, series in macro['series'].items():
    print(f"\n{indicator_name}:")
    for point in series:
        print(f"  {point['period']}: {point['value']}{point['unit']}")
```

### 6. 向量检索

#### 全库语义检索

```python
from agent import search_documents

# 检索与"ADC药物研发进展"相关的文档
results = search_documents(
    query="ADC药物研发进展",
    stock_code="600276",
    doc_types=["announcement", "news"],
    top_k=5
)

for result in results:
    print(f"文档类型: {result['doc_type']}")
    print(f"相似度: {result['score']}")
    print(f"内容片段: {result['content'][:100]}...")
    print("---")
```

#### 检索公司证据

```python
from agent import search_company_evidence

# 检索公司相关的证据
evidence = search_company_evidence(
    query="集采影响分析",
    stock_code="600276",
    top_k=5
)

for item in evidence:
    print(f"来源: {item['doc_type']}")
    print(f"内容: {item['content'][:150]}...")
    print("---")
```

---

## 提示词模板使用

### 1. 系统提示词

```python
from agent import PromptTemplates

# 获取基础系统提示词
system_prompt = PromptTemplates.SYSTEM_BASE
print(system_prompt)
```

### 2. 公司全面分析

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

### 3. 财务深度分析

```python
from agent import PromptTemplates

# 构建财务分析提示词
prompt = PromptTemplates.build_financial_analysis_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 包含盈利能力、成长性、现金流、资产质量等维度
print(prompt)
```

### 4. 药品管线分析

```python
from agent import PromptTemplates

# 构建药品管线分析提示词
prompt = PromptTemplates.build_drug_pipeline_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 包含已上市产品、在研管线、竞争分析等
print(prompt)
```

### 5. 政策影响分析

```python
from agent import PromptTemplates

# 构建政策影响分析提示词
prompt = PromptTemplates.build_policy_impact_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 包含集采、医保谈判、DRG/DIP等政策影响
print(prompt)
```

### 6. 行业对比分析

```python
from agent import PromptTemplates

# 构建行业对比分析提示词
prompt = PromptTemplates.build_industry_comparison_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 包含财务指标、估值、业务、风险等多维度对比
print(prompt)
```

### 7. 风险预警分析

```python
from agent import PromptTemplates

# 构建风险预警分析提示词
prompt = PromptTemplates.build_risk_warning_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 包含财务、经营、政策、法律、市场等风险类别
print(prompt)
```

### 8. 快速查询

```python
from agent import PromptTemplates

# 构建快速查询提示词
prompt = PromptTemplates.build_quick_query_prompt(
    query="恒瑞医药最近有哪些新药获批？"
)

# 简明扼要的查询提示词
print(prompt)
```

---

## Agent集成示例

### 示例1：使用GLMMinimalAgent

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
print(f"图表描述: {result['chart_desc']}")
print(f"报告: {result['report_markdown']}")
```

### 示例2：自定义Agent实现

```python
from agent import (
    PromptTemplates,
    get_company_overview,
    get_financial_summary,
    get_drug_approvals,
    search_company_evidence,
)

class CustomPharmaceuticalAgent:
    """自定义医药分析Agent"""
    
    def analyze_company(self, stock_code: str):
        """公司全面分析"""
        
        # 1. 获取公司信息
        overview = get_company_overview(stock_code)
        stock_name = overview['stock_name']
        
        # 2. 获取财务数据
        financial = get_financial_summary(stock_code, period_count=4)
        
        # 3. 获取药品批准
        approvals = get_drug_approvals(stock_code, days=365)
        
        # 4. 检索补充证据
        evidence = search_company_evidence(
            query=f"{stock_name} 研发管线 财务分析",
            stock_code=stock_code,
            top_k=5
        )
        
        # 5. 构建分析提示词
        prompt = PromptTemplates.build_company_analysis_prompt(
            stock_code=stock_code,
            stock_name=stock_name
        )
        
        # 6. 组织分析结果
        analysis = {
            "company": overview,
            "financial": financial,
            "drug_approvals": approvals,
            "evidence": evidence,
            "prompt": prompt,
        }
        
        return analysis
    
    def analyze_drug_pipeline(self, stock_code: str):
        """药品管线分析"""
        
        # 1. 获取公司信息
        overview = get_company_overview(stock_code)
        stock_name = overview['stock_name']
        
        # 2. 获取药品批准和临床试验
        from agent import get_drug_approvals, get_clinical_trials
        
        approvals = get_drug_approvals(stock_code, days=365)
        trials = get_clinical_trials(stock_code, days=365)
        
        # 3. 检索研发相关证据
        evidence = search_company_evidence(
            query=f"{stock_name} 药品研发 临床试验 新药批准",
            stock_code=stock_code,
            top_k=10
        )
        
        # 4. 构建分析提示词
        prompt = PromptTemplates.build_drug_pipeline_prompt(
            stock_code=stock_code,
            stock_name=stock_name
        )
        
        # 5. 组织分析结果
        pipeline_analysis = {
            "company": overview,
            "drug_approvals": approvals,
            "clinical_trials": trials,
            "evidence": evidence,
            "prompt": prompt,
        }
        
        return pipeline_analysis

# 使用自定义Agent
agent = CustomPharmaceuticalAgent()
analysis = agent.analyze_company("600276")
print(f"分析完成，获取到 {len(analysis['drug_approvals'])} 个药品批准事件")
```

### 示例3：LangChain集成

```python
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent import (
    get_company_overview,
    get_financial_summary,
    get_drug_approvals,
    search_company_evidence,
    PromptTemplates,
)

# 定义工具
tools = [
    Tool(
        name="get_company_overview",
        func=lambda stock_code: get_company_overview(stock_code),
        description="获取公司完整概览，包括基本信息、业务概述、行业分类。输入：股票代码（6位数字）"
    ),
    Tool(
        name="get_financial_summary",
        func=lambda stock_code: get_financial_summary(stock_code, period_count=4),
        description="获取公司财务数据汇总，包括利润表、资产负债表、现金流量表、关键指标。输入：股票代码"
    ),
    Tool(
        name="get_drug_approvals",
        func=lambda stock_code: get_drug_approvals(stock_code, days=365),
        description="获取公司最近1年的药品批准事件。输入：股票代码"
    ),
    Tool(
        name="search_company_evidence",
        func=lambda args: search_company_evidence(
            query=args.split("|")[0],
            stock_code=args.split("|")[1],
            top_k=5
        ),
        description="检索公司相关证据（公告、财务附注等）。输入：查询文本|股票代码"
    ),
]

# 创建Agent
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt_template = PromptTemplate.from_template(
    PromptTemplates.SYSTEM_BASE + "\n\n{input}\n\n{agent_scratchpad}"
)

agent = create_react_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 运行查询
result = agent_executor.invoke({
    "input": "分析恒瑞医药（600276）的研发管线和财务状况"
})

print(result["output"])
```

### 示例4：流式输出Agent

```python
from agent import (
    PromptTemplates,
    get_company_overview,
    get_financial_summary,
    get_company_event_summary,
)

class StreamingAnalysisAgent:
    """支持流式输出的分析Agent"""
    
    def analyze_with_streaming(self, stock_code: str):
        """流式输出分析结果"""
        
        # 1. 获取公司信息
        yield "正在获取公司信息...\n"
        overview = get_company_overview(stock_code)
        stock_name = overview['stock_name']
        yield f"公司名称: {stock_name}\n"
        yield f"所属行业: {overview['industry_level1']} - {overview['industry_level2']}\n\n"
        
        # 2. 获取财务数据
        yield "正在获取财务数据...\n"
        financial = get_financial_summary(stock_code, period_count=4)
        latest = financial['latest_income']
        yield f"最新营业收入: {latest['revenue']}\n"
        yield f"最新净利润: {latest['net_profit']}\n"
        yield f"研发费用: {latest['rd_expense']}\n\n"
        
        # 3. 获取事件汇总
        yield "正在获取公告事件...\n"
        events = get_company_event_summary(stock_code, days=365)
        yield f"药品批准数: {len(events['drug_approvals'])}\n"
        yield f"临床试验数: {len(events['clinical_trials'])}\n"
        yield f"集采事件数: {len(events['procurement_events'])}\n\n"
        
        # 4. 生成分析报告
        yield "正在生成分析报告...\n"
        prompt = PromptTemplates.build_company_analysis_prompt(
            stock_code=stock_code,
            stock_name=stock_name
        )
        yield f"\n分析框架:\n{prompt}\n"

# 使用流式Agent
agent = StreamingAnalysisAgent()
for chunk in agent.analyze_with_streaming("600276"):
    print(chunk, end="", flush=True)
```

---

## 最佳实践

### 1. 错误处理

```python
from agent import get_company_overview

def safe_get_company_info(stock_code: str):
    """安全获取公司信息，带错误处理"""
    try:
        overview = get_company_overview(stock_code)
        return {"success": True, "data": overview}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {str(e)}"}

# 使用
result = safe_get_company_info("600276")
if result["success"]:
    print(f"公司名称: {result['data']['stock_name']}")
else:
    print(f"获取失败: {result['error']}")
```

### 2. 数据缓存

```python
from functools import lru_cache
from agent import get_financial_summary

@lru_cache(maxsize=100)
def cached_get_financial_summary(stock_code: str, period_count: int = 4):
    """带缓存的财务数据获取"""
    return get_financial_summary(stock_code, period_count)

# 第一次调用会查询数据库
financial1 = cached_get_financial_summary("600276")

# 第二次调用直接返回缓存
financial2 = cached_get_financial_summary("600276")
```

### 3. 批量处理

```python
from agent import get_company_overview, get_financial_summary

def batch_analyze_companies(stock_codes: list[str]):
    """批量分析多家公司"""
    results = []
    
    for stock_code in stock_codes:
        try:
            overview = get_company_overview(stock_code)
            financial = get_financial_summary(stock_code, period_count=4)
            
            results.append({
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "revenue": financial['latest_income']['revenue'],
                "net_profit": financial['latest_income']['net_profit'],
            })
        except Exception as e:
            print(f"处理 {stock_code} 失败: {e}")
            continue
    
    return results

# 批量分析医药龙头
pharma_leaders = ["600276", "000661", "002821", "300015"]
results = batch_analyze_companies(pharma_leaders)

for result in results:
    print(f"{result['stock_name']}: 收入={result['revenue']}, 利润={result['net_profit']}")
```

### 4. 组合查询

```python
from agent import (
    get_company_overview,
    get_financial_summary,
    get_company_event_summary,
    get_company_news_impact,
)

def comprehensive_analysis(stock_code: str):
    """综合分析：组合多个数据源"""
    
    # 并行获取多个数据源（实际可用异步）
    overview = get_company_overview(stock_code)
    financial = get_financial_summary(stock_code, period_count=4)
    events = get_company_event_summary(stock_code, days=365)
    news = get_company_news_impact(stock_code, days=90)
    
    # 综合评分
    score = 0
    
    # 财务评分（40分）
    if financial['latest_income']['net_profit'] > 0:
        score += 20
    if financial['latest_cashflow']['operating_cashflow'] > 0:
        score += 20
    
    # 事件评分（30分）
    score += min(len(events['drug_approvals']) * 5, 15)
    score += min(len(events['opportunity_items']) * 3, 15)
    
    # 舆情评分（30分）
    positive_ratio = news['direction_counts'].get('positive', 0) / max(len(news['items']), 1)
    score += int(positive_ratio * 30)
    
    return {
        "stock_code": stock_code,
        "stock_name": overview['stock_name'],
        "comprehensive_score": score,
        "overview": overview,
        "financial": financial,
        "events": events,
        "news": news,
    }

# 使用
analysis = comprehensive_analysis("600276")
print(f"综合评分: {analysis['comprehensive_score']}/100")
```

### 5. 提示词定制

```python
from agent import PromptTemplates

class CustomPromptTemplates(PromptTemplates):
    """自定义提示词模板"""
    
    # 扩展基础系统提示词
    SYSTEM_BASE = PromptTemplates.SYSTEM_BASE + """
    
## 额外能力
- 支持中英文双语分析
- 提供量化评分（0-100分）
- 生成可视化图表建议
"""
    
    # 自定义分析模板
    CUSTOM_ANALYSIS = """# 自定义分析任务

## 分析目标
{custom_objective}

## 分析要求
{custom_requirements}

## 数据获取
{data_sources}

## 输出格式
{output_format}
"""
    
    @staticmethod
    def build_custom_analysis_prompt(
        objective: str,
        requirements: str,
        data_sources: str,
        output_format: str
    ) -> str:
        """构建自定义分析提示词"""
        return CustomPromptTemplates.format_template(
            CustomPromptTemplates.CUSTOM_ANALYSIS,
            custom_objective=objective,
            custom_requirements=requirements,
            data_sources=data_sources,
            output_format=output_format,
        )

# 使用自定义模板
prompt = CustomPromptTemplates.build_custom_analysis_prompt(
    objective="评估CXO企业的订单饱和度",
    requirements="分析订单金额、产能利用率、客户结构",
    data_sources="财务数据、业务分部、公司公告",
    output_format="Markdown表格 + 评分 + 建议"
)
print(prompt)
```

---

## 常见问题

### Q1: 如何处理股票代码格式？

A: 工具函数接受6位数字的股票代码字符串，如 "600519"、"000661"。如果用户输入包含市场前缀（如 "SH600519"），需要先提取6位数字部分。

```python
def normalize_stock_code(code: str) -> str:
    """标准化股票代码"""
    # 移除市场前缀
    code = code.replace("SH", "").replace("SZ", "")
    # 确保6位数字
    if len(code) == 6 and code.isdigit():
        return code
    raise ValueError(f"无效的股票代码: {code}")
```

### Q2: 如何选择合适的提示词模板？

A: 根据用户问题类型选择：
- 全面了解公司 → `COMPANY_ANALYSIS`
- 财务指标分析 → `FINANCIAL_ANALYSIS`
- 研发管线评估 → `DRUG_PIPELINE_ANALYSIS`
- 政策影响评估 → `POLICY_IMPACT_ANALYSIS`
- 横向对比 → `INDUSTRY_COMPARISON`
- 风险识别 → `RISK_WARNING`
- 简单查询 → `QUICK_QUERY`

### Q3: 如何优化查询性能？

A: 
1. 使用缓存避免重复查询
2. 批量查询时使用异步并发
3. 限制返回数据量（limit参数）
4. 优先使用汇总接口（如 `get_financial_summary`）

### Q4: 如何集成到现有Agent框架？

A: 工具函数设计为框架无关，可以轻松集成到：
- LangChain: 包装为 `Tool` 对象
- LlamaIndex: 包装为 `FunctionTool`
- AutoGPT: 注册为插件命令
- 自定义Agent: 直接调用函数

---

## 更多示例

完整示例代码请参考：
- `backend/examples/agent_examples.py` - Agent使用示例
- `backend/examples/tool_examples.py` - 工具函数示例
- `backend/examples/prompt_examples.py` - 提示词示例

## 技术支持

如有问题，请联系开发团队或提交Issue。
