"""提示词模板使用示例"""

from __future__ import annotations

import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def example_system_prompt():
    """系统提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("系统提示词示例")
    print("=" * 50)

    print("\n基础系统提示词:")
    print(PromptTemplates.SYSTEM_BASE)


def example_company_analysis_prompt():
    """公司分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("公司全面分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_company_analysis_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt)


def example_financial_analysis_prompt():
    """财务分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("财务深度分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_financial_analysis_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt[:500] + "...\n(已截断)")


def example_drug_pipeline_prompt():
    """药品管线分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("药品管线分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_drug_pipeline_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt[:500] + "...\n(已截断)")


def example_policy_impact_prompt():
    """政策影响分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("政策影响分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_policy_impact_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt[:500] + "...\n(已截断)")


def example_industry_comparison_prompt():
    """行业对比分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("行业对比分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_industry_comparison_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt[:500] + "...\n(已截断)")


def example_risk_warning_prompt():
    """风险预警分析提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("风险预警分析提示词示例")
    print("=" * 50)

    prompt = PromptTemplates.build_risk_warning_prompt(
        stock_code="600276",
        stock_name="恒瑞医药"
    )

    print("\n生成的提示词:")
    print(prompt[:500] + "...\n(已截断)")


def example_quick_query_prompt():
    """快速查询提示词示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("快速查询提示词示例")
    print("=" * 50)

    queries = [
        "恒瑞医药最近有哪些新药获批？",
        "分析药明康德的订单情况",
        "集采对某某公司的影响有多大？",
    ]

    for query in queries:
        print(f"\n查询: {query}")
        prompt = PromptTemplates.build_quick_query_prompt(query)
        print(f"提示词: {prompt[:200]}...\n")


def example_custom_template():
    """自定义模板示例"""
    from agent.prompts import PromptTemplates

    print("=" * 50)
    print("自定义模板示例")
    print("=" * 50)

    # 使用format_template方法自定义模板
    custom_template = """
# {analysis_type}分析

## 分析对象
公司: {stock_name} ({stock_code})

## 分析维度
{dimensions}

## 数据来源
{data_sources}
"""

    result = PromptTemplates.format_template(
        custom_template,
        analysis_type="CXO企业",
        stock_name="药明康德",
        stock_code="603259",
        dimensions="订单饱和度、产能利用率、客户结构",
        data_sources="财务数据、业务分部、公司公告"
    )

    print("\n自定义模板结果:")
    print(result)


if __name__ == "__main__":
    print("运行提示词模板示例...\n")

    try:
        example_system_prompt()
    except Exception as e:
        print(f"系统提示词示例失败: {e}")

    try:
        example_company_analysis_prompt()
    except Exception as e:
        print(f"公司分析提示词示例失败: {e}")

    try:
        example_financial_analysis_prompt()
    except Exception as e:
        print(f"财务分析提示词示例失败: {e}")

    try:
        example_drug_pipeline_prompt()
    except Exception as e:
        print(f"药品管线提示词示例失败: {e}")

    try:
        example_policy_impact_prompt()
    except Exception as e:
        print(f"政策影响提示词示例失败: {e}")

    try:
        example_industry_comparison_prompt()
    except Exception as e:
        print(f"行业对比提示词示例失败: {e}")

    try:
        example_risk_warning_prompt()
    except Exception as e:
        print(f"风险预警提示词示例失败: {e}")

    try:
        example_quick_query_prompt()
    except Exception as e:
        print(f"快速查询提示词示例失败: {e}")

    try:
        example_custom_template()
    except Exception as e:
        print(f"自定义模板示例失败: {e}")
