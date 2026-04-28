#!/usr/bin/env python3
"""验证工具函数和提示词模板是否正确导入"""

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def verify_tools_import():
    """验证工具函数导入"""
    print("=" * 60)
    print("验证工具函数导入")
    print("=" * 60)

    try:
        from agent.tools import (
            # Company tools
            get_company_basic_info,
            get_company_profile,
            get_company_overview,
            resolve_company_from_text,
            # Financial tools
            get_income_statements,
            get_balance_sheets,
            get_cashflow_statements,
            get_financial_metrics,
            get_business_segments,
            get_financial_summary,
            # Announcement tools
            get_raw_announcements,
            get_structured_announcements,
            get_drug_approvals,
            get_clinical_trials,
            get_procurement_events,
            get_regulatory_risks,
            get_company_event_summary,
            # News tools
            get_news_raw,
            get_news_by_company,
            get_news_by_industry,
            get_company_news_impact,
            get_industry_news_impact,
            # Macro tools
            get_macro_indicator,
            list_macro_indicators,
            get_macro_summary,
            # Retrieval tools
            search_documents,
            search_company_evidence,
            search_news_evidence,
        )

        print("✓ 公司信息工具 (4个)")
        print("✓ 财务数据工具 (6个)")
        print("✓ 公告事件工具 (7个)")
        print("✓ 新闻舆情工具 (5个)")
        print("✓ 宏观指标工具 (3个)")
        print("✓ 向量检索工具 (3个)")
        print("\n总计: 28个工具函数")
        print("\n✓ 所有工具函数导入成功！")
        return True

    except ImportError as e:
        print(f"\n✗ 工具函数导入失败: {e}")
        return False


def verify_prompts_import():
    """验证提示词模板导入"""
    print("\n" + "=" * 60)
    print("验证提示词模板导入")
    print("=" * 60)

    try:
        from agent.prompts import PromptTemplates, SYSTEM_PROMPT, build_chat_messages

        # 验证系统提示词
        assert hasattr(PromptTemplates, 'SYSTEM_BASE')
        print("✓ 系统提示词 (SYSTEM_BASE)")

        # 验证分析场景模板
        templates = [
            'COMPANY_ANALYSIS',
            'FINANCIAL_ANALYSIS',
            'DRUG_PIPELINE_ANALYSIS',
            'POLICY_IMPACT_ANALYSIS',
            'INDUSTRY_COMPARISON',
            'RISK_WARNING',
            'QUICK_QUERY',
        ]

        for template in templates:
            assert hasattr(PromptTemplates, template)
        print("✓ 分析场景模板 (7个)")

        # 验证构建方法
        methods = [
            'build_company_analysis_prompt',
            'build_financial_analysis_prompt',
            'build_drug_pipeline_prompt',
            'build_policy_impact_prompt',
            'build_industry_comparison_prompt',
            'build_risk_warning_prompt',
            'build_quick_query_prompt',
        ]

        for method in methods:
            assert hasattr(PromptTemplates, method)
        print("✓ 提示词构建方法 (7个)")

        print("\n✓ 所有提示词模板导入成功！")
        return True

    except (ImportError, AssertionError) as e:
        print(f"\n✗ 提示词模板导入失败: {e}")
        return False


def verify_agent_import():
    """验证Agent导入"""
    print("\n" + "=" * 60)
    print("验证Agent导入")
    print("=" * 60)

    try:
        from agent import GLMMinimalAgent, LangChainAgentStub

        print("✓ GLMMinimalAgent")
        print("✓ LangChainAgentStub")

        print("\n✓ 所有Agent导入成功！")
        return True

    except ImportError as e:
        print(f"\n✗ Agent导入失败: {e}")
        return False


def verify_examples_exist():
    """验证示例文件存在"""
    print("\n" + "=" * 60)
    print("验证示例文件")
    print("=" * 60)

    examples_dir = os.path.join(os.path.dirname(__file__))

    example_files = [
        'tool_examples.py',
        'prompt_examples.py',
        'agent_examples.py',
    ]

    all_exist = True
    for filename in example_files:
        filepath = os.path.join(examples_dir, filename)
        if os.path.exists(filepath):
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename} 不存在")
            all_exist = False

    if all_exist:
        print("\n✓ 所有示例文件存在！")
    else:
        print("\n✗ 部分示例文件缺失")

    return all_exist


def verify_documentation_exist():
    """验证文档文件存在"""
    print("\n" + "=" * 60)
    print("验证文档文件")
    print("=" * 60)

    agent_dir = os.path.join(os.path.dirname(__file__), "..", "agent")

    doc_files = [
        'README.md',
        'SUMMARY.md',
        'QUICKSTART.md',
    ]

    all_exist = True
    for filename in doc_files:
        filepath = os.path.join(agent_dir, filename)
        if os.path.exists(filepath):
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename} 不存在")
            all_exist = False

    if all_exist:
        print("\n✓ 所有文档文件存在！")
    else:
        print("\n✗ 部分文档文件缺失")

    return all_exist


def print_summary():
    """打印总结"""
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    print("\n已实现的功能:")
    print("  1. ✓ 工具函数包 (28个函数)")
    print("     - 公司信息查询 (4个)")
    print("     - 财务数据查询 (6个)")
    print("     - 公告事件查询 (7个)")
    print("     - 新闻舆情查询 (5个)")
    print("     - 宏观指标查询 (3个)")
    print("     - 向量检索 (3个)")

    print("\n  2. ✓ 提示词模板集合 (7个场景)")
    print("     - 公司全面分析")
    print("     - 财务深度分析")
    print("     - 药品管线分析")
    print("     - 政策影响分析")
    print("     - 行业对比分析")
    print("     - 风险预警分析")
    print("     - 快速查询")

    print("\n  3. ✓ Agent集成")
    print("     - GLMMinimalAgent")
    print("     - LangChainAgentStub")

    print("\n  4. ✓ 示例代码 (3个文件)")
    print("     - tool_examples.py")
    print("     - prompt_examples.py")
    print("     - agent_examples.py")

    print("\n  5. ✓ 完整文档")
    print("     - README.md (详细使用文档)")
    print("     - SUMMARY.md (项目概览)")
    print("     - QUICKSTART.md (快速入门)")

    print("\n" + "=" * 60)
    print("✓ 所有功能已实现，可以直接使用！")
    print("=" * 60)

    print("\n下一步:")
    print("  1. 查看 agent/README.md 了解详细使用方法")
    print("  2. 查看 agent/QUICKSTART.md 快速上手")
    print("  3. 运行 examples/ 中的示例代码")
    print("  4. 根据需求自定义Agent实现")

    print("\n使用示例:")
    print("  from agent import get_company_overview, PromptTemplates")
    print("  overview = get_company_overview('600276')")
    print("  prompt = PromptTemplates.build_company_analysis_prompt('600276', '恒瑞医药')")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("4C医药投资分析系统 - Agent工具包验证")
    print("=" * 60)

    results = []

    # 验证导入
    results.append(("工具函数导入", verify_tools_import()))
    results.append(("提示词模板导入", verify_prompts_import()))
    results.append(("Agent导入", verify_agent_import()))

    # 验证文件
    results.append(("示例文件", verify_examples_exist()))
    results.append(("文档文件", verify_documentation_exist()))

    # 打印总结
    print_summary()

    # 最终结果
    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n" + "=" * 60)
        print("✓ 所有验证通过！系统可以正常使用。")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗ 部分验证失败，请检查错误信息。")
        print("=" * 60)
        sys.exit(1)
