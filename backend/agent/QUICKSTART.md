# 快速入门指南

## 5分钟快速上手

### 第一步：导入工具函数

```python
# 导入所需的工具函数
from agent import (
    get_company_overview,
    get_financial_summary,
    get_drug_approvals,
    search_company_evidence,
)

# 获取公司信息
company = get_company_overview("600276")
print(f"公司名称: {company['stock_name']}")
print(f"所属行业: {company['industry_level1']}")
```

### 第二步：使用提示词模板

```python
from agent import PromptTemplates

# 生成公司分析提示词
prompt = PromptTemplates.build_company_analysis_prompt(
    stock_code="600276",
    stock_name="恒瑞医药"
)

# 提示词包含完整的分析框架
print(prompt)
```

### 第三步：运行Agent

```python
from agent import GLMMinimalAgent

# 初始化Agent
agent = GLMMinimalAgent()

# 执行分析
result = agent.run(
    message="分析恒瑞医药的研发管线和财务状况",
    targets=[{"type": "stock", "symbol": "600276"}],
    current_stock_code="600276",
    user_id=1,
    session_id=1001
)

# 查看结果
print(result['answer'])
print(result['suggestion'])
```

## 常见使用场景

### 场景1：公司基本面分析

```python
from agent import (
    get_company_overview,
    get_financial_summary,
    get_company_event_summary,
    PromptTemplates,
)

def analyze_company_fundamentals(stock_code: str):
    """公司基本面分析"""
    
    # 1. 获取公司信息
    overview = get_company_overview(stock_code)
    stock_name = overview['stock_name']
    
    # 2. 获取财务数据
    financial = get_financial_summary(stock_code, period_count=4)
    
    # 3. 获取事件汇总
    events = get_company_event_summary(stock_code, days=365)
    
    # 4. 生成分析报告
    print(f"\n{'='*50}")
    print(f"{stock_name} 基本面分析")
    print(f"{'='*50}")
    
    print(f"\n【公司概况】")
    print(f"  行业: {overview['industry_level1']} - {overview['industry_level2']}")
    
    print(f"\n【财务状况】")
    latest = financial['latest_income']
    print(f"  营业收入: {latest['revenue']}")
    print(f"  净利润: {latest['net_profit']}")
    print(f"  研发费用: {latest['rd_expense']}")
    
    print(f"\n【重要事件】")
    print(f"  药品批准: {len(events['drug_approvals'])}个")
    print(f"  临床试验: {len(events['clinical_trials'])}个")
    print(f"  集采事件: {len(events['procurement_events'])}个")
    
    return {
        "overview": overview,
        "financial": financial,
        "events": events,
    }

# 使用
result = analyze_company_fundamentals("600276")
```

### 场景2：药品管线评估

```python
from agent import (
    get_drug_approvals,
    get_clinical_trials,
    search_company_evidence,
    PromptTemplates,
)

def evaluate_drug_pipeline(stock_code: str):
    """药品管线评估"""
    
    # 1. 获取药品批准
    approvals = get_drug_approvals(stock_code, days=365)
    
    # 2. 获取临床试验
    trials = get_clinical_trials(stock_code, days=365)
    
    # 3. 检索研发证据
    evidence = search_company_evidence(
        query="药品研发 临床试验 新药批准",
        stock_code=stock_code,
        top_k=5
    )
    
    # 4. 生成评估报告
    print(f"\n{'='*50}")
    print(f"药品管线评估")
    print(f"{'='*50}")
    
    print(f"\n【药品批准】共{len(approvals)}个")
    for appr in approvals[:3]:
        print(f"  - {appr['drug_name']}: {appr['approval_type']} ({appr['indication']})")
    
    print(f"\n【临床试验】共{len(trials)}个")
    for trial in trials[:3]:
        print(f"  - {trial['drug_name']} {trial['trial_phase']}: {trial['event_type']}")
    
    print(f"\n【管线评分】")
    score = len(approvals) * 10 + len(trials) * 5
    print(f"  综合评分: {score}分")
    
    return {
        "approvals": approvals,
        "trials": trials,
        "evidence": evidence,
        "score": score,
    }

# 使用
result = evaluate_drug_pipeline("600276")
```

### 场景3：财务健康度评估

```python
from agent import (
    get_financial_summary,
    get_financial_metrics,
    PromptTemplates,
)

def assess_financial_health(stock_code: str):
    """财务健康度评估"""
    
    # 1. 获取财务汇总
    financial = get_financial_summary(stock_code, period_count=4)
    
    # 2. 获取关键指标
    metrics = get_financial_metrics(
        stock_code,
        metric_names=["gross_margin", "net_margin", "roe", "rd_ratio", "debt_ratio"],
        limit=4
    )
    
    # 3. 计算健康度评分
    score = 0
    
    latest_income = financial['latest_income']
    latest_balance = financial['latest_balance']
    latest_cashflow = financial['latest_cashflow']
    
    # 盈利能力（30分）
    if latest_income['net_profit'] > 0:
        score += 15
    if latest_income['gross_profit'] > 0:
        score += 15
    
    # 资产质量（30分）
    if latest_balance['total_assets'] > latest_balance['total_liabilities']:
        score += 30
    
    # 现金流（20分）
    if latest_cashflow['operating_cashflow'] > 0:
        score += 20
    
    # 研发投入（20分）
    if latest_income['rd_expense'] > 0:
        score += 20
    
    # 4. 生成评估报告
    print(f"\n{'='*50}")
    print(f"财务健康度评估")
    print(f"{'='*50}")
    
    print(f"\n【综合评分】{score}/100分")
    
    print(f"\n【盈利能力】")
    print(f"  营业收入: {latest_income['revenue']}")
    print(f"  净利润: {latest_income['net_profit']}")
    print(f"  毛利润: {latest_income['gross_profit']}")
    
    print(f"\n【资产质量】")
    print(f"  总资产: {latest_balance['total_assets']}")
    print(f"  总负债: {latest_balance['total_liabilities']}")
    print(f"  股东权益: {latest_balance['equity']}")
    
    print(f"\n【现金流】")
    print(f"  经营现金流: {latest_cashflow['operating_cashflow']}")
    print(f"  自由现金流: {latest_cashflow['free_cashflow']}")
    
    print(f"\n【研发投入】")
    print(f"  研发费用: {latest_income['rd_expense']}")
    
    return {
        "score": score,
        "financial": financial,
        "metrics": metrics,
    }

# 使用
result = assess_financial_health("600276")
```

### 场景4：政策影响分析

```python
from agent import (
    get_procurement_events,
    get_regulatory_risks,
    get_company_news_impact,
    PromptTemplates,
)

def analyze_policy_impact(stock_code: str):
    """政策影响分析"""
    
    # 1. 获取集采事件
    procurements = get_procurement_events(stock_code, days=365)
    
    # 2. 获取监管风险
    risks = get_regulatory_risks(stock_code, days=365)
    
    # 3. 获取新闻影响
    news = get_company_news_impact(stock_code, days=90)
    
    # 4. 生成分析报告
    print(f"\n{'='*50}")
    print(f"政策影响分析")
    print(f"{'='*50}")
    
    print(f"\n【集采影响】共{len(procurements)}个事件")
    for proc in procurements[:3]:
        print(f"  - {proc['drug_name']}: {proc['bid_result']} (价格变化: {proc['price_change_ratio']})")
    
    print(f"\n【监管风险】共{len(risks)}个事件")
    for risk in risks[:3]:
        print(f"  - {risk['risk_type']}: {risk['risk_level']}")
    
    print(f"\n【舆情影响】")
    print(f"  影响方向: {news['direction_counts']}")
    print(f"  平均强度: {news['avg_impact_strength']}")
    
    # 计算政策风险评分
    risk_score = 100 - (len(procurements) * 5 + len(risks) * 10)
    risk_score = max(0, min(100, risk_score))
    
    print(f"\n【政策风险评分】{risk_score}/100分")
    
    return {
        "procurements": procurements,
        "risks": risks,
        "news": news,
        "risk_score": risk_score,
    }

# 使用
result = analyze_policy_impact("600276")
```

### 场景5：行业对比分析

```python
from agent import (
    get_company_overview,
    get_financial_summary,
    PromptTemplates,
)

def compare_companies(stock_codes: list[str]):
    """行业对比分析"""
    
    results = []
    
    for stock_code in stock_codes:
        try:
            overview = get_company_overview(stock_code)
            financial = get_financial_summary(stock_code, period_count=4)
            
            latest = financial['latest_income']
            
            results.append({
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "revenue": latest['revenue'],
                "net_profit": latest['net_profit'],
                "rd_expense": latest['rd_expense'],
            })
        except Exception as e:
            print(f"处理 {stock_code} 失败: {e}")
    
    # 生成对比报告
    print(f"\n{'='*50}")
    print(f"行业对比分析")
    print(f"{'='*50}\n")
    
    print(f"{'公司名称':<15} {'营业收入':<15} {'净利润':<15} {'研发费用':<15}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['stock_name']:<15} {str(r['revenue']):<15} {str(r['net_profit']):<15} {str(r['rd_expense']):<15}")
    
    return results

# 使用 - 对比医药龙头
pharma_leaders = ["600276", "000661", "002821", "300015"]
results = compare_companies(pharma_leaders)
```

## 最佳实践

### 1. 错误处理

```python
def safe_analysis(stock_code: str):
    """带错误处理的分析"""
    try:
        overview = get_company_overview(stock_code)
        return {"success": True, "data": overview}
    except ValueError as e:
        return {"success": False, "error": f"数据错误: {e}"}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {e}"}
```

### 2. 数据缓存

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_get_company_info(stock_code: str):
    """带缓存的公司信息获取"""
    return get_company_overview(stock_code)
```

### 3. 批量处理

```python
def batch_process(stock_codes: list[str]):
    """批量处理多家公司"""
    results = []
    for code in stock_codes:
        try:
            data = get_company_overview(code)
            results.append(data)
        except Exception as e:
            print(f"处理 {code} 失败: {e}")
    return results
```

### 4. 组合查询

```python
def comprehensive_query(stock_code: str):
    """组合多个数据源"""
    return {
        "company": get_company_overview(stock_code),
        "financial": get_financial_summary(stock_code),
        "events": get_company_event_summary(stock_code),
        "news": get_company_news_impact(stock_code),
    }
```

## 下一步

- 查看 [README.md](README.md) 了解完整文档
- 查看 [SUMMARY.md](SUMMARY.md) 了解项目概览
- 运行 [examples/](../examples/) 中的示例代码
- 根据需求自定义Agent实现

## 常见问题

**Q: 如何处理股票代码格式？**  
A: 使用6位数字格式，如"600519"。

**Q: 如何选择合适的提示词模板？**  
A: 根据分析目标选择：全面分析用COMPANY_ANALYSIS，财务分析用FINANCIAL_ANALYSIS，等等。

**Q: 如何优化查询性能？**  
A: 使用缓存、限制返回数据量、优先使用汇总接口。

**Q: 如何集成到现有系统？**  
A: 工具函数设计为框架无关，可直接导入使用。
