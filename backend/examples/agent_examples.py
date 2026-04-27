"""Agent集成使用示例"""

from __future__ import annotations

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def example_glm_minimal_agent():
    """GLMMinimalAgent使用示例"""
    from agent.integration import GLMMinimalAgent

    print("=" * 50)
    print("GLMMinimalAgent使用示例")
    print("=" * 50)

    # 初始化Agent
    agent = GLMMinimalAgent()

    # 示例1: 基本查询
    print("\n示例1: 基本查询")
    result = agent.run(
        message="分析恒瑞医药的研发管线",
        targets=[{"type": "stock", "symbol": "600276"}],
        current_stock_code="600276",
        user_id=1,
        session_id=1001
    )

    print(f"回答: {result.get('answer', '')[:200]}...")
    print(f"建议: {result.get('suggestion', '')[:100]}...")
    print(f"框架: {result.get('framework')}")
    print(f"模式: {result.get('agent_mode')}")

    # 示例2: 带历史对话
    print("\n示例2: 带历史对话")
    history = [
        {"role": "user", "content": "恒瑞医药是做什么的？"},
        {"role": "assistant", "content": "恒瑞医药是中国领先的创新药企业..."},
    ]

    result = agent.run(
        message="它的研发投入怎么样？",
        targets=[{"type": "stock", "symbol": "600276"}],
        current_stock_code="600276",
        history=history,
        user_id=1,
        session_id=1001
    )

    print(f"回答: {result.get('answer', '')[:200]}...")


def example_custom_agent():
    """自定义Agent实现示例"""
    from agent.tools import (
        get_company_overview,
        get_financial_summary,
        get_drug_approvals,
        get_clinical_trials,
        search_company_evidence,
    )
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("自定义Agent实现示例")
    print("=" * 50)

    class PharmaceuticalAnalysisAgent:
        """医药企业分析Agent"""

        def analyze_company(self, stock_code: str) -> dict:
            """公司全面分析"""
            print(f"\n正在分析 {stock_code}...")

            # 1. 获取公司信息
            print("  - 获取公司信息")
            overview = get_company_overview(stock_code)
            stock_name = overview['stock_name']

            # 2. 获取财务数据
            print("  - 获取财务数据")
            financial = get_financial_summary(stock_code, period_count=4)

            # 3. 获取研发管线
            print("  - 获取研发管线")
            approvals = get_drug_approvals(stock_code, days=365)
            trials = get_clinical_trials(stock_code, days=365)

            # 4. 检索补充证据
            print("  - 检索补充证据")
            evidence = search_company_evidence(
                query=f"{stock_name} 研发管线 财务分析",
                stock_code=stock_code,
                top_k=5
            )

            # 5. 生成分析报告
            print("  - 生成分析报告")
            report = self._generate_report(
                overview, financial, approvals, trials, evidence
            )

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "overview": overview,
                "financial": financial,
                "drug_approvals": approvals,
                "clinical_trials": trials,
                "evidence": evidence,
                "report": report,
            }

        def _generate_report(self, overview, financial, approvals, trials, evidence):
            """生成分析报告"""
            stock_name = overview['stock_name']
            latest_income = financial.get('latest_income') or {}

            report = f"""
# {stock_name} 投资分析报告

## 一、公司概况
- 公司名称: {stock_name}
- 所属行业: {overview.get('industry_level1')} - {overview.get('industry_level2')}
- 业务概述: {str(overview.get('profile', {}).get('business_summary', ''))[:100]}...

## 二、财务状况
- 营业收入: {latest_income.get('revenue')}
- 净利润: {latest_income.get('net_profit')}
- 研发费用: {latest_income.get('rd_expense')}
- 毛利率: {latest_income.get('gross_profit')}

## 三、研发管线
- 药品批准数: {len(approvals)}
- 临床试验数: {len(trials)}

## 四、投资建议
基于以上分析，建议关注该公司的研发进展和财务表现。

**本报告仅供参考，不构成投资建议**
"""
            return report

    # 使用自定义Agent
    agent = PharmaceuticalAnalysisAgent()
    result = agent.analyze_company("600276")

    print("\n分析结果:")
    print(result['report'])


def example_streaming_agent():
    """流式输出Agent示例"""
    from agent.tools import (
        get_company_overview,
        get_financial_summary,
        get_company_event_summary,
    )

    print("=" * 50)
    print("流式输出Agent示例")
    print("=" * 50)

    class StreamingAnalysisAgent:
        """支持流式输出的分析Agent"""

        def analyze_with_streaming(self, stock_code: str):
            """流式输出分析结果"""

            # 1. 获取公司信息
            yield "\n正在获取公司信息...\n"
            overview = get_company_overview(stock_code)
            stock_name = overview['stock_name']
            yield f"✓ 公司名称: {stock_name}\n"
            yield f"✓ 所属行业: {overview['industry_level1']} - {overview['industry_level2']}\n"

            # 2. 获取财务数据
            yield "\n正在获取财务数据...\n"
            financial = get_financial_summary(stock_code, period_count=4)
            latest = financial.get('latest_income') or {}
            yield f"✓ 最新营业收入: {latest.get('revenue')}\n"
            yield f"✓ 最新净利润: {latest.get('net_profit')}\n"
            yield f"✓ 研发费用: {latest.get('rd_expense')}\n"

            # 3. 获取事件汇总
            yield "\n正在获取公告事件...\n"
            events = get_company_event_summary(stock_code, days=365)
            yield f"✓ 药品批准数: {len(events.get('drug_approvals', []))}\n"
            yield f"✓ 临床试验数: {len(events.get('clinical_trials', []))}\n"
            yield f"✓ 集采事件数: {len(events.get('procurement_events', []))}\n"

            # 4. 生成总结
            yield "\n分析完成！\n"
            yield f"\n{stock_name} 是一家{overview['industry_level1']}企业，"
            yield f"最新营业收入为{latest.get('revenue')}，"
            yield f"研发投入为{latest.get('rd_expense')}。"
            yield f"近一年共有{len(events.get('drug_approvals', []))}个药品获批。\n"

    # 使用流式Agent
    agent = StreamingAnalysisAgent()
    for chunk in agent.analyze_with_streaming("600276"):
        print(chunk, end="", flush=True)


def example_batch_analysis_agent():
    """批量分析Agent示例"""
    from agent.tools import (
        get_company_overview,
        get_financial_summary,
    )

    print("=" * 50)
    print("批量分析Agent示例")
    print("=" * 50)

    class BatchAnalysisAgent:
        """批量分析Agent"""

        def batch_analyze(self, stock_codes: list[str]) -> list[dict]:
            """批量分析多家公司"""
            results = []

            for stock_code in stock_codes:
                try:
                    print(f"\n正在分析 {stock_code}...")

                    overview = get_company_overview(stock_code)
                    financial = get_financial_summary(stock_code, period_count=4)

                    latest_income = financial.get('latest_income') or {}

                    results.append({
                        "stock_code": stock_code,
                        "stock_name": overview['stock_name'],
                        "industry": f"{overview['industry_level1']}-{overview['industry_level2']}",
                        "revenue": latest_income.get('revenue'),
                        "net_profit": latest_income.get('net_profit'),
                        "rd_expense": latest_income.get('rd_expense'),
                    })

                    print(f"  ✓ {overview['stock_name']} 分析完成")

                except Exception as e:
                    print(f"  ✗ {stock_code} 分析失败: {e}")
                    continue

            return results

        def compare_companies(self, results: list[dict]):
            """对比分析结果"""
            print("\n\n对比分析结果:")
            print("-" * 80)
            print(f"{'公司名称':<15} {'行业':<20} {'营业收入':<15} {'净利润':<15}")
            print("-" * 80)

            for r in results:
                print(f"{r['stock_name']:<15} {r['industry']:<20} {str(r['revenue']):<15} {str(r['net_profit']):<15}")

            print("-" * 80)

    # 使用批量分析Agent
    agent = BatchAnalysisAgent()

    # 分析医药龙头企业
    pharma_leaders = ["600276", "000661", "002821", "300015"]
    results = agent.batch_analyze(pharma_leaders)

    # 对比分析
    agent.compare_companies(results)


def example_multi_strategy_agent():
    """多策略Agent示例"""
    from agent.tools import (
        get_company_overview,
        get_financial_summary,
        get_drug_approvals,
        get_company_news_impact,
    )
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("多策略Agent示例")
    print("=" * 50)

    class MultiStrategyAgent:
        """多策略分析Agent"""

        def analyze(self, stock_code: str, strategy: str = "comprehensive"):
            """根据策略进行分析"""

            if strategy == "comprehensive":
                return self._comprehensive_analysis(stock_code)
            elif strategy == "financial":
                return self._financial_analysis(stock_code)
            elif strategy == "pipeline":
                return self._pipeline_analysis(stock_code)
            elif strategy == "sentiment":
                return self._sentiment_analysis(stock_code)
            else:
                raise ValueError(f"未知策略: {strategy}")

        def _comprehensive_analysis(self, stock_code: str):
            """综合分析策略"""
            print(f"\n执行综合分析策略: {stock_code}")

            overview = get_company_overview(stock_code)
            financial = get_financial_summary(stock_code, period_count=4)
            approvals = get_drug_approvals(stock_code, days=365)
            news = get_company_news_impact(stock_code, days=90)

            score = self._calculate_comprehensive_score(financial, approvals, news)

            return {
                "strategy": "comprehensive",
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "score": score,
                "data": {
                    "overview": overview,
                    "financial": financial,
                    "approvals": approvals,
                    "news": news,
                }
            }

        def _financial_analysis(self, stock_code: str):
            """财务分析策略"""
            print(f"\n执行财务分析策略: {stock_code}")

            overview = get_company_overview(stock_code)
            financial = get_financial_summary(stock_code, period_count=4)

            score = self._calculate_financial_score(financial)

            return {
                "strategy": "financial",
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "score": score,
                "data": {"financial": financial}
            }

        def _pipeline_analysis(self, stock_code: str):
            """管线分析策略"""
            print(f"\n执行管线分析策略: {stock_code}")

            overview = get_company_overview(stock_code)
            approvals = get_drug_approvals(stock_code, days=365)

            score = len(approvals) * 10  # 简单评分

            return {
                "strategy": "pipeline",
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "score": score,
                "data": {"approvals": approvals}
            }

        def _sentiment_analysis(self, stock_code: str):
            """舆情分析策略"""
            print(f"\n执行舆情分析策略: {stock_code}")

            overview = get_company_overview(stock_code)
            news = get_company_news_impact(stock_code, days=90)

            direction_counts = news.get('direction_counts', {})
            positive = direction_counts.get('positive', 0)
            negative = direction_counts.get('negative', 0)
            total = positive + negative + direction_counts.get('neutral', 0)

            score = int((positive / max(total, 1)) * 100)

            return {
                "strategy": "sentiment",
                "stock_code": stock_code,
                "stock_name": overview['stock_name'],
                "score": score,
                "data": {"news": news}
            }

        def _calculate_comprehensive_score(self, financial, approvals, news):
            """计算综合评分"""
            score = 0

            # 财务评分（40分）
            latest_income = financial.get('latest_income') or {}
            if latest_income.get('net_profit', 0) > 0:
                score += 20
            if latest_income.get('rd_expense', 0) > 0:
                score += 20

            # 管线评分（30分）
            score += min(len(approvals) * 5, 30)

            # 舆情评分（30分）
            direction_counts = news.get('direction_counts', {})
            positive = direction_counts.get('positive', 0)
            total = sum(direction_counts.values())
            if total > 0:
                score += int((positive / total) * 30)

            return score

        def _calculate_financial_score(self, financial):
            """计算财务评分"""
            score = 0

            latest_income = financial.get('latest_income') or {}
            latest_balance = financial.get('latest_balance') or {}
            latest_cashflow = financial.get('latest_cashflow') or {}

            # 盈利能力（40分）
            if latest_income.get('net_profit', 0) > 0:
                score += 20
            if latest_income.get('gross_profit', 0) > 0:
                score += 20

            # 资产质量（30分）
            if latest_balance.get('total_assets', 0) > latest_balance.get('total_liabilities', 0):
                score += 30

            # 现金流（30分）
            if latest_cashflow.get('operating_cashflow', 0) > 0:
                score += 30

            return score

    # 使用多策略Agent
    agent = MultiStrategyAgent()

    # 测试不同策略
    strategies = ["comprehensive", "financial", "pipeline", "sentiment"]

    for strategy in strategies:
        try:
            result = agent.analyze("600276", strategy=strategy)
            print(f"\n策略: {result['strategy']}")
            print(f"公司: {result['stock_name']}")
            print(f"评分: {result['score']}")
        except Exception as e:
            print(f"\n策略 {strategy} 执行失败: {e}")


if __name__ == "__main__":
    print("运行Agent集成示例...\n")
    print("注意：需要数据库连接和LLM配置才能运行这些示例\n")

    try:
        example_glm_minimal_agent()
    except Exception as e:
        print(f"GLMMinimalAgent示例失败: {e}")

    try:
        example_custom_agent()
    except Exception as e:
        print(f"自定义Agent示例失败: {e}")

    try:
        example_streaming_agent()
    except Exception as e:
        print(f"流式Agent示例失败: {e}")

    try:
        example_batch_analysis_agent()
    except Exception as e:
        print(f"批量分析Agent示例失败: {e}")

    try:
        example_multi_strategy_agent()
    except Exception as e:
        print(f"多策略Agent示例失败: {e}")
