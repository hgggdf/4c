"""工具函数使用示例"""

from __future__ import annotations

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def example_company_tools():
    """公司信息工具示例"""
    from agent.tools import (
        get_company_basic_info,
        get_company_overview,
        get_company_profile,
        resolve_company_from_text,
    )

    print("=" * 50)
    print("公司信息工具示例")
    print("=" * 50)

    # 1. 获取基本信息
    print("\n1. 获取公司基本信息")
    info = get_company_basic_info("600276")
    print(f"  股票代码: {info['stock_code']}")
    print(f"  公司名称: {info['stock_name']}")
    print(f"  一级行业: {info['industry_level1']}")
    print(f"  二级行业: {info['industry_level2']}")

    # 2. 获取公司资料
    print("\n2. 获取公司详细资料")
    profile = get_company_profile("600276")
    if profile:
        print(f"  业务概述: {str(profile.get('business_summary', ''))[:80]}...")
        print(f"  市场地位: {profile.get('market_position', '')}")

    # 3. 获取完整概览
    print("\n3. 获取公司完整概览")
    overview = get_company_overview("600276")
    print(f"  行业分类数: {len(overview.get('industries', []))}")
    print(f"  是否有资料: {overview.get('profile') is not None}")

    # 4. 从文本识别公司
    print("\n4. 从文本识别公司")
    companies = resolve_company_from_text("恒瑞医药")
    if companies:
        print(f"  识别到 {len(companies)} 家公司")
        print(f"  第一个: {companies[0]['stock_name']} ({companies[0]['stock_code']})")


def example_financial_tools():
    """财务数据工具示例"""
    from agent.tools import (
        get_balance_sheets,
        get_business_segments,
        get_cashflow_statements,
        get_financial_metrics,
        get_financial_summary,
        get_income_statements,
    )

    print("=" * 50)
    print("财务数据工具示例")
    print("=" * 50)

    # 1. 利润表
    print("\n1. 获取利润表（最近4期）")
    income = get_income_statements("600276", limit=4)
    for row in income[:2]:
        print(f"  {row['report_date']}: 收入={row['revenue']}, 净利润={row['net_profit']}")

    # 2. 资产负债表
    print("\n2. 获取资产负债表（最近4期）")
    balance = get_balance_sheets("600276", limit=4)
    for row in balance[:2]:
        print(f"  {row['report_date']}: 总资产={row['total_assets']}, 负债率={row['total_liabilities']}")

    # 3. 现金流量表
    print("\n3. 获取现金流量表（最近4期）")
    cashflow = get_cashflow_statements("600276", limit=4)
    for row in cashflow[:2]:
        print(f"  {row['report_date']}: 经营现金流={row['operating_cashflow']}")

    # 4. 财务指标
    print("\n4. 获取关键财务指标")
    metrics = get_financial_metrics(
        "600276",
        metric_names=["gross_margin", "net_margin", "roe", "rd_ratio"],
        limit=4,
    )
    for m in metrics[:4]:
        print(f"  {m['report_date']} {m['metric_name']}: {m['metric_value']}{m.get('metric_unit', '')}")

    # 5. 业务分部
    print("\n5. 获取业务分部数据")
    segments = get_business_segments("600276", limit=4)
    for seg in segments[:3]:
        print(f"  {seg['segment_name']}: 收入占比={seg['revenue_ratio']}, 毛利率={seg['gross_margin']}")

    # 6. 财务汇总
    print("\n6. 获取财务汇总")
    summary = get_financial_summary("600276", period_count=4)
    latest = summary.get("latest_income") or {}
    print(f"  最新营业收入: {latest.get('revenue')}")
    print(f"  最新净利润: {latest.get('net_profit')}")
    print(f"  研发费用: {latest.get('rd_expense')}")


def example_announcement_tools():
    """公告事件工具示例"""
    from agent.tools import (
        get_clinical_trials,
        get_company_event_summary,
        get_drug_approvals,
        get_procurement_events,
        get_regulatory_risks,
        get_structured_announcements,
    )

    print("=" * 50)
    print("公告事件工具示例")
    print("=" * 50)

    # 1. 结构化公告
    print("\n1. 获取结构化公告（最近365天）")
    announcements = get_structured_announcements("600276", days=365)
    print(f"  共 {len(announcements)} 条结构化公告")
    for ann in announcements[:2]:
        print(f"  [{ann.get('signal_type')}] {ann.get('category')}: {str(ann.get('summary_text', ''))[:60]}...")

    # 2. 药品批准
    print("\n2. 获取药品批准事件")
    approvals = get_drug_approvals("600276", days=365)
    print(f"  共 {len(approvals)} 个药品批准事件")
    for appr in approvals[:2]:
        print(f"  {appr.get('drug_name')} - {appr.get('approval_type')} - {appr.get('indication')}")

    # 3. 临床试验
    print("\n3. 获取临床试验事件")
    trials = get_clinical_trials("600276", days=365)
    print(f"  共 {len(trials)} 个临床试验事件")
    for trial in trials[:2]:
        print(f"  {trial.get('drug_name')} {trial.get('trial_phase')}: {trial.get('event_type')}")

    # 4. 集采事件
    print("\n4. 获取集采中标事件")
    procurements = get_procurement_events("600276", days=365)
    print(f"  共 {len(procurements)} 个集采事件")
    for proc in procurements[:2]:
        print(f"  {proc.get('drug_name')} - {proc.get('bid_result')} - 价格变化: {proc.get('price_change_ratio')}")

    # 5. 监管风险
    print("\n5. 获取监管风险事件")
    risks = get_regulatory_risks("600276", days=365)
    print(f"  共 {len(risks)} 个监管风险事件")

    # 6. 事件汇总
    print("\n6. 获取公司事件汇总")
    summary = get_company_event_summary("600276", days=365)
    print(f"  机会类公告: {len(summary.get('opportunity_items', []))}")
    print(f"  风险类公告: {len(summary.get('risk_items', []))}")
    print(f"  按分类统计: {summary.get('counts_by_category', {})}")


def example_news_tools():
    """新闻舆情工具示例"""
    from agent.tools import (
        get_company_news_impact,
        get_industry_news_impact,
        get_news_by_company,
        get_news_by_industry,
        get_news_raw,
    )

    print("=" * 50)
    print("新闻舆情工具示例")
    print("=" * 50)

    # 1. 原始新闻
    print("\n1. 获取原始新闻（最近30天）")
    news = get_news_raw(days=30)
    print(f"  共 {len(news)} 条新闻")
    for n in news[:2]:
        print(f"  [{n.get('news_type')}] {n.get('title')}")

    # 2. 公司新闻
    print("\n2. 获取公司相关新闻")
    company_news = get_news_by_company("600276", days=90)
    print(f"  共 {len(company_news)} 条公司新闻")
    for n in company_news[:2]:
        print(f"  [{n.get('impact_direction')}] {n.get('title')} (强度: {n.get('impact_strength')})")

    # 3. 行业新闻
    print("\n3. 获取行业新闻")
    industry_news = get_news_by_industry("C27", days=30)
    print(f"  共 {len(industry_news)} 条行业新闻")

    # 4. 公司新闻影响分析
    print("\n4. 获取公司新闻影响分析")
    impact = get_company_news_impact("600276", days=90)
    print(f"  影响方向统计: {impact.get('direction_counts', {})}")
    print(f"  平均影响强度: {impact.get('avg_impact_strength')}")

    # 5. 行业新闻影响分析
    print("\n5. 获取行业新闻影响分析")
    industry_impact = get_industry_news_impact("C27", days=30)
    print(f"  行业影响方向统计: {industry_impact.get('direction_counts', {})}")


def example_macro_tools():
    """宏观指标工具示例"""
    from agent.tools import (
        get_macro_indicator,
        get_macro_summary,
        list_macro_indicators,
    )

    print("=" * 50)
    print("宏观指标工具示例")
    print("=" * 50)

    # 1. 单个指标
    print("\n1. 获取单个宏观指标")
    indicator = get_macro_indicator("GDP增速")
    if indicator:
        print(f"  {indicator['indicator_name']}: {indicator['value']}{indicator.get('unit', '')}")
        print(f"  期间: {indicator['period']}")

    # 2. 批量指标
    print("\n2. 批量获取宏观指标")
    indicators = list_macro_indicators(["CPI", "PPI", "PMI"])
    for ind in indicators:
        print(f"  {ind['indicator_name']} ({ind['period']}): {ind['value']}{ind.get('unit', '')}")

    # 3. 指标汇总（时间序列）
    print("\n3. 获取宏观指标时间序列")
    summary = get_macro_summary(["GDP增速", "CPI"], recent_n=4)
    for name, series in summary.get("series", {}).items():
        print(f"\n  {name}:")
        for point in series:
            print(f"    {point['period']}: {point['value']}{point.get('unit', '')}")


def example_retrieval_tools():
    """向量检索工具示例"""
    from agent.tools import (
        search_company_evidence,
        search_documents,
        search_news_evidence,
    )

    print("=" * 50)
    print("向量检索工具示例")
    print("=" * 50)

    # 1. 全库检索
    print("\n1. 全库语义检索")
    results = search_documents(
        query="ADC药物研发进展",
        stock_code="600276",
        doc_types=["announcement", "news"],
        top_k=3,
    )
    print(f"  检索到 {len(results)} 条结果")
    for r in results:
        print(f"  [{r.get('doc_type')}] 相似度={r.get('score'):.3f}: {str(r.get('content', ''))[:60]}...")

    # 2. 公司证据检索
    print("\n2. 公司证据检索")
    evidence = search_company_evidence(
        query="集采影响分析",
        stock_code="600276",
        top_k=3,
    )
    print(f"  检索到 {len(evidence)} 条证据")
    for e in evidence:
        print(f"  [{e.get('doc_type')}] {str(e.get('content', ''))[:60]}...")

    # 3. 新闻证据检索
    print("\n3. 新闻证据检索")
    news_evidence = search_news_evidence(
        query="医保谈判政策影响",
        stock_code="600276",
        top_k=3,
    )
    print(f"  检索到 {len(news_evidence)} 条新闻证据")
    for n in news_evidence:
        print(f"  [{n.get('source_name')}] {n.get('title')}")


if __name__ == "__main__":
    print("运行工具函数示例...\n")
    print("注意：需要数据库连接才能运行这些示例\n")

    try:
        example_company_tools()
    except Exception as e:
        print(f"公司工具示例失败: {e}")

    try:
        example_financial_tools()
    except Exception as e:
        print(f"财务工具示例失败: {e}")

    try:
        example_announcement_tools()
    except Exception as e:
        print(f"公告工具示例失败: {e}")

    try:
        example_news_tools()
    except Exception as e:
        print(f"新闻工具示例失败: {e}")

    try:
        example_macro_tools()
    except Exception as e:
        print(f"宏观工具示例失败: {e}")

    try:
        example_retrieval_tools()
    except Exception as e:
        print(f"检索工具示例失败: {e}")
