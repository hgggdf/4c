"""Agent提示词模板集合 - 针对不同分析场景的结构化提示词"""

from __future__ import annotations

from typing import Any


class PromptTemplates:
    """医药投资分析Agent提示词模板库"""

    # ==================== 系统提示词 ====================

    SYSTEM_BASE = """你是"智策系统"——专注于医药生物行业的智能投资分析助手。

## 你的能力
1. **公司基本面分析**：解读财务指标（ROE、毛利率、研发投入比、应收账款周转率等），识别异常风险
2. **管线与研发分析**：分析药品管线（ADC、CAR-T、PD-1等）的研发阶段、适应症、竞争格局
3. **政策影响分析**：解读医保谈判、集采、DRG/DIP等政策对企业的影响
4. **行业对比**：横向对比同类公司的关键指标，判断估值位置
5. **实时行情**：结合当前股价、涨跌幅、成交量给出短线观察
6. **CXO赛道**：分析CXO企业订单、产能、客户结构变化

## 回答原则
- 优先结合具体数据（财务指标、股价、研报）给出有依据的分析
- 对于研发管线，说明品种、阶段、适应症、竞争对手
- 对于财务分析，重点关注ROE分解、研发费用率、现金流质量
- 明确区分事实陈述和分析判断
- 每次回答末尾注明：**本回答仅供参考，不构成投资建议**

## 可用工具
你可以调用以下工具函数获取数据：
- 公司信息：get_company_basic_info, get_company_profile, get_company_overview, resolve_company_from_text
- 财务数据：get_income_statements, get_balance_sheets, get_cashflow_statements, get_financial_metrics, get_financial_summary
- 公告事件：get_drug_approvals, get_clinical_trials, get_procurement_events, get_regulatory_risks, get_company_event_summary
- 新闻舆情：get_news_by_company, get_company_news_impact, get_industry_news_impact
- 宏观指标：get_macro_indicator, list_macro_indicators, get_macro_summary
- 向量检索：search_documents, search_company_evidence, search_news_evidence
"""

    # ==================== 公司分析提示词 ====================

    COMPANY_ANALYSIS = """# 公司全面分析任务

## 分析目标
对 {stock_code} {stock_name} 进行全面的投资价值分析。

## 分析框架
请按以下结构组织分析：

### 1. 公司概况
- 基本信息：股票代码、公司全称、所属行业、上市时间
- 业务概述：主营业务、核心产品、市场地位
- 行业分类：一级行业、二级行业、细分赛道

### 2. 财务健康度分析
- 盈利能力：营业收入、净利润、毛利率、净利率趋势（最近4期）
- 成长性：收入增速、利润增速、ROE变化
- 现金流：经营性现金流、自由现金流质量
- 资产质量：应收账款、存货、商誉占比
- 研发投入：研发费用率、研发费用绝对值变化

### 3. 研发管线分析（医药企业重点）
- 药品批准：最近1年内获批的新药、适应症、创新药情况
- 临床试验：在研管线的试验阶段、进展情况
- 竞争格局：同类药物的竞争对手、市场空间

### 4. 政策与事件影响
- 集采影响：中标情况、价格变化、对业绩的影响
- 监管风险：是否存在处罚、警告、调查等风险事件
- 重大公告：最近的重要公告及其影响

### 5. 新闻舆情
- 正面新闻：利好消息、行业机会
- 负面新闻：风险提示、市场担忧
- 舆情趋势：整体舆论倾向

### 6. 投资建议
- 核心优势：3个最突出的投资亮点
- 主要风险：3个需要关注的风险点
- 估值判断：当前估值水平是否合理
- 操作建议：买入/持有/观望的理由

## 数据获取步骤
1. 调用 get_company_overview 获取公司基本信息和业务概述
2. 调用 get_financial_summary 获取最近4期财务数据
3. 调用 get_company_event_summary 获取最近1年的公告和事件
4. 调用 get_company_news_impact 获取最近90天的新闻影响
5. 调用 search_company_evidence 检索补充证据

## 输出要求
- 使用Markdown格式组织内容
- 关键数据用表格展示
- 重要结论用加粗标注
- 末尾注明：**本分析仅供参考，不构成投资建议**
"""

    FINANCIAL_ANALYSIS = """# 财务深度分析任务

## 分析目标
对 {stock_code} {stock_name} 进行深度财务分析，识别财务风险和投资机会。

## 分析维度

### 1. 盈利能力分析
- 毛利率：最近4期毛利率变化趋势，与行业平均对比
- 净利率：净利率变化，扣非净利润占比
- 期间费用率：销售费用率、管理费用率、研发费用率
- ROE分解：杜邦分析（净利率×总资产周转率×权益乘数）

### 2. 成长性分析
- 收入增速：最近4期营业收入同比增速
- 利润增速：净利润同比增速，是否高于收入增速
- 业务分部：各业务板块的收入占比和增速
- 成长驱动力：收入增长的主要来源（量/价/新产品）

### 3. 现金流分析
- 经营性现金流：与净利润的匹配度
- 自由现金流：经营现金流-资本支出
- 现金流质量：收现比、付现比
- 资金压力：短期偿债能力、流动比率

### 4.资产质量分析
- 应收账款：应收账款占收入比例，周转天数
- 存货：存货占总资产比例，周转率
- 商誉：商誉占净资产比例，减值风险
- 资产负债率：负债结构，有息负债占比

### 5. 研发投入分析（医药企业）
- 研发费用率：研发费用/营业收入
- 研发费用绝对值：同比变化
- 研发资本化率：资本化研发支出占比
- 研发产出：新药获批数量、临床试验进展

### 6. 财务风险预警
- 收入确认风险：应收账款异常增长
- 利润质量风险：扣非净利润持续为负
- 现金流风险：经营现金流持续为负
- 商誉减值风险：商誉占比过高
- 债务风险：资产负债率过高、短期偿债压力

## 数据获取步骤
1. 调用 get_financial_summary 获取完整财务数据
2. 调用 get_financial_metrics 获取关键财务指标：
   - ["gross_margin", "net_margin", "rd_ratio", "roe", "debt_ratio", "receivable_turnover", "inventory_turnover"]
3. 调用 get_business_segments 获取业务分部数据
4. 调用 search_documents 检索财务附注中的风险提示

## 输出要求
- 使用表格展示关键财务指标的4期数据
- 用图表描述趋势（如果可能）
- 标注异常指标和风险点
- 给出财务健康度评分（0-100分）
"""

    DRUG_PIPELINE_ANALYSIS = """# 药品管线分析任务

## 分析目标
对 {stock_code} {stock_name} 的药品研发管线进行全面梳理和评估。

## 分析框架

### 1. 已上市产品
- 核心产品：产品名称、适应症、市场地位
- 销售贡献：各产品的收入占比
- 竞争格局：同类产品的竞争对手、市场份额
- 集采影响：是否纳入集采、价格变化

### 2. 在研管线
- I期临床：在研品种、适应症、预计进度
- II期临床：在研品种、适应症、预计进度
- III期临床：在研品种、适应症、预计进度
- 申报上市：已提交上市申请的品种

### 3. 近期进展
- 药品批准：最近1年获批的新药
- 临床试验：最近1年的临床试验进展
- 研发里程碑：重要的研发节点事件

### 4. 技术平台
- 核心技术：ADC、CAR-T、PD-1/PD-L1、小分子等
- 技术优势：相比竞争对手的技术壁垒
- 研发投入：研发费用率、研发团队规模

### 5. 竞争分析
- 同类企业：主要竞争对手的管线对比
- 差异化优势：独特的适应症、技术路线
- 市场空间：目标适应症的市场规模

### 6. 管线价值评估
- 短期催化剂：1年内可能获批的品种
- 中期潜力：2-3年内的管线价值
- 长期布局：战略性布局的新技术平台
- 风险提示：临床失败风险、竞争加剧风险

## 数据获取步骤
1. 调用 get_company_profile 获取核心产品信息
2. 调用 get_drug_approvals 获取最近1年的药品批准
3. 调用 get_clinical_trials 获取最近1年的临床试验进展
4. 调用 search_company_evidence 检索研发管线相关公告
5. 调用 get_business_segments 获取产品线收入结构

## 输出要求
- 用表格展示在研管线（品种、阶段、适应症、预计时间）
- 标注重点品种（First-in-class、Best-in-class）
- 评估管线的丰富度和创新性
- 给出管线价值评分（0-100分）
"""

    POLICY_IMPACT_ANALYSIS = """# 政策影响分析任务

## 分析目标
分析医药政策（集采、医保谈判、DRG/DIP等）对 {stock_code} {stock_name} 的影响。

## 分析框架

### 1. 集采影响分析
- 中标情况：哪些产品中标、中标价格
- 价格变化：降价幅度、对毛利率的影响
- 销量变化：以量补价的效果
- 业绩影响：对收入和利润的定量影响
- 应对策略：公司的应对措施

### 2. 医保谈判影响
- 谈判结果：哪些产品进入医保目录
- 价格调整：医保谈判价格变化
- 市场准入：医保覆盖带来的市场扩容
- 放量预期：进入医保后的销量预测

### 3. DRG/DIP影响
- 支付方式改革：对用药结构的影响
- 产品影响：哪些产品受益、哪些受损
- 医院端反馈：医院采购行为的变化

### 4. 其他政策影响
- 创新药政策：优先审评、突破性疗法认定
- 一致性评价：通过情况、市场影响
- 两票制/带量采购：对流通环节的影响
- 监管政策：GMP认证、飞行检查等

### 5. 行业政策趋势
- 政策方向：鼓励创新、控制费用
- 未来预期：可能的政策变化
- 行业影响：对整个医药行业的影响

### 6. 应对建议
- 短期应对：如何应对当前政策压力
- 长期布局：如何调整产品结构
- 风险对冲：多元化布局、创新转型

## 数据获取步骤
1. 调用 get_procurement_events 获取集采中标情况
2. 调用 get_structured_announcements 获取政策相关公告
3. 调用 get_company_news_impact 获取政策新闻影响
4. 调用 search_documents 检索政策影响的详细分析
5. 调用 get_financial_summary 评估政策对财务的影响

## 输出要求
- 用表格展示集采中标产品和价格变化
- 定量分析对收入和利润的影响
- 评估公司的政策应对能力
- 给出政策风险评分（0-100分，分数越低风险越高）
"""

    INDUSTRY_COMPARISON = """# 行业对比分析任务

## 分析目标
将 {stock_code} {stock_name} 与同行业可比公司进行横向对比，判断相对投资价值。

## 对比维度

### 1. 财务指标对比
- 盈利能力：毛利率、净利率、ROE
- 成长性：收入增速、利润增速
- 研发投入：研发费用率、研发费用绝对值
- 现金流：经营现金流/净利润
- 资产质量：应收账款周转率、存货周转率

### 2. 估值对比
- PE（市盈率）：当前PE、历史PE分位
- PB（市净率）：当前PB、历史PB分位
- PS（市销率）：适用于亏损企业
- PEG：PE/净利润增速
- 估值溢价/折价：相对行业平均的溢价率

### 3. 业务对比
- 产品结构：核心产品的市场地位
- 研发管线：在研品种的数量和质量
- 市场份额：在细分领域的市场占有率
- 客户结构：客户集中度、客户质量

### 4. 政策影响对比
- 集采影响：受集采影响的产品占比
- 创新能力：创新药占比、First-in-class数量
- 政策受益：是否受益于政策扶持

### 5. 风险对比
- 商誉风险：商誉占净资产比例
- 债务风险：资产负债率、有息负债率
- 监管风险：是否存在监管处罚
- 经营风险：应收账款风险、存货风险

### 6. 综合评分
- 财务健康度：0-100分
- 成长潜力：0-100分
- 估值吸引力：0-100分
- 风险水平：0-100分（分数越低风险越高）
- 综合评分：加权平均分

## 数据获取步骤
1. 确定可比公司列表（同行业、同赛道）
2. 对每家公司调用 get_financial_summary 获取财务数据
3. 对每家公司调用 get_company_event_summary 获取事件数据
4. 调用 get_industry_news_impact 获取行业整体新闻
5. 调用 search_documents 检索行业研报和对比分析

## 输出要求
- 用对比表格展示关键指标（目标公司 vs 可比公司平均）
- 用雷达图展示多维度评分（如果可能）
- 标注目标公司的相对优势和劣势
- 给出相对投资价值排名
"""

    RISK_WARNING = """# 风险预警分析任务

## 分析目标
全面识别 {stock_code} {stock_name} 的投资风险，提供风险预警。

## 风险类别

### 1. 财务风险
- 盈利质量风险：扣非净利润持续为负、利润依赖非经常性损益
- 现金流风险：经营现金流持续为负、自由现金流恶化
- 应收账款风险：应收账款占比过高、账龄恶化、坏账风险
- 存货风险：存货占比过高、周转率下降、减值风险
- 商誉风险：商誉占净资产比例过高、减值风险
- 债务风险：资产负债率过高、短期偿债压力、利息覆盖率低

### 2. 经营风险
- 收入依赖风险：单一产品占比过高、客户集中度高
- 市场竞争风险：竞争加剧、市场份额下降
- 产品降价风险：集采降价、医保谈判降价
- 研发失败风险：重点品种临床失败、研发进度延迟
- 供应链风险：原材料涨价、供应商集中度高

### 3. 政策风险
- 集采风险：核心产品面临集采、降价压力
- 医保控费风险：医保支付压力、用药限制
- 监管风险：GMP认证、飞行检查、质量问题
- 环保风险：环保政策趋严、生产限制

### 4. 法律与合规风险
- 诉讼风险：专利诉讼、商业纠纷
- 处罚风险：监管处罚、行政处罚
- 合规风险：财务造假、信息披露违规
- 商业贿赂风险：医药行业特有的合规风险

### 5. 市场风险
- 估值风险：估值过高、泡沫风险
- 流动性风险：成交量萎缩、大股东减持
- 系统性风险：行业整体下行、市场情绪恶化

### 6. 其他风险
- 管理层风险：核心高管离职、内部治理问题
- 关联交易风险：关联交易占比过高、利益输送
- 商誉减值风险：并购标的业绩不达预期

## 风险评估方法

### 风险等级划分
- 高风险：可能导致投资本金重大损失
- 中风险：可能导致投资收益显著下降
- 低风险：对投资影响有限

### 风险评分
- 每类风险评分：0-100分（分数越低风险越高）
- 综合风险评分：加权平均
- 风险预警阈值：<60分为高风险，60-80分为中风险，>80分为低风险

## 数据获取步骤
1. 调用 get_financial_summary 识别财务风险指标
2. 调用 get_regulatory_risks 获取监管风险事件
3. 调用 get_company_event_summary 获取所有风险事件
4. 调用 get_company_news_impact 获取负面新闻
5. 调用 search_documents 检索风险提示和预警信息

## 输出要求
- 按风险等级分类列示（高/中/低）
- 每个风险点说明：风险描述、影响程度、应对建议
- 给出综合风险评分和风险等级
- 提供风险监控指标和预警阈值
"""

    QUICK_QUERY = """# 快速查询任务

## 查询内容
{query}

## 分析要求
- 直接回答用户问题，简明扼要
- 优先使用具体数据支撑结论
- 如果数据不足，明确说明
- 控制回答长度在300字以内

## 数据获取策略
根据问题类型选择合适的工具：
- 公司基本信息 → get_company_overview
- 财务数据 → get_financial_summary
- 研发管线 → get_drug_approvals, get_clinical_trials
- 政策影响 → get_procurement_events, get_regulatory_risks
- 新闻舆情 → get_company_news_impact
- 宏观数据 → get_macro_indicator
- 模糊查询 → search_documents

## 输出要求
- 直接给出答案，不需要完整的分析框架
- 关键数据用加粗标注
- 如需详细分析，建议用户使用完整分析模板
"""

    # ==================== 工具函数 ====================

    @staticmethod
    def format_template(template: str, **kwargs: Any) -> str:
        """
        格式化提示词模板

        Args:
            template: 模板字符串
            **kwargs: 模板变量

        Returns:
            格式化后的提示词
        """
        return template.format(**kwargs)

    @staticmethod
    def build_company_analysis_prompt(stock_code: str, stock_name: str) -> str:
        """构建公司分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.COMPANY_ANALYSIS,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_financial_analysis_prompt(stock_code: str, stock_name: str) -> str:
        """构建财务分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.FINANCIAL_ANALYSIS,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_drug_pipeline_prompt(stock_code: str, stock_name: str) -> str:
        """构建药品管线分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.DRUG_PIPELINE_ANALYSIS,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_policy_impact_prompt(stock_code: str, stock_name: str) -> str:
        """构建政策影响分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.POLICY_IMPACT_ANALYSIS,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_industry_comparison_prompt(stock_code: str, stock_name: str) -> str:
        """构建行业对比分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.INDUSTRY_COMPARISON,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_risk_warning_prompt(stock_code: str, stock_name: str) -> str:
        """构建风险预警分析提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.RISK_WARNING,
            stock_code=stock_code,
            stock_name=stock_name,
        )

    @staticmethod
    def build_quick_query_prompt(query: str) -> str:
        """构建快速查询提示词"""
        return PromptTemplates.format_template(
            PromptTemplates.QUICK_QUERY,
            query=query,
        )


__all__ = ["PromptTemplates"]
