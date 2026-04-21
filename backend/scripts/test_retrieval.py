"""检索能力烟测脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge.retriever import hybrid_search, route_query, search_unstructured

TEST_CASES = [
    ("恒瑞医药2024年毛利率是多少", "structured"),
    ("药明康德2023年净利润", "structured"),
    ("爱尔眼科2022年ROE", "structured"),
    ("对比三家公司2024年毛利率", "structured"),
    ("恒瑞医药近三年营业总收入趋势", "structured"),
    ("CPI和GDP宏观数据", "structured"),
    ("恒瑞医药的研发管线分析", "unstructured"),
    ("药明康德集采风险和投资价值", "unstructured"),
    ("医药行业政策对CXO的影响", "unstructured"),
    ("恒瑞医药2023年毛利率多少，以及行业风险", "hybrid"),
]


def _preview_result(result) -> str:
    if isinstance(result, list):
        if not result:
            return "无非结构化命中"
        return str(result[0].get("text", ""))[:120].replace("\n", " ")

    if isinstance(result, dict):
        hits = result.get("unstructured_hits") or []
        if hits:
            return str(hits[0].get("text", ""))[:120].replace("\n", " ")
        return f"route={result.get('route')} year={result.get('year')}"

    return str(result)[:120].replace("\n", " ")


def run_tests() -> None:
    print("=" * 70)
    print("检索能力烟测")
    print("=" * 70)

    pass_count = 0
    fail_count = 0

    for index, (query, expected_route) in enumerate(TEST_CASES, 1):
        actual_route = route_query(query)
        route_ok = actual_route == expected_route

        if actual_route == "unstructured":
            result = search_unstructured(query, top_k=2)
        else:
            result = hybrid_search(query, top_k=2)

        print(f"\n[{index:02d}] 问题：{query}")
        print(f"     路由：期望={expected_route}，实际={actual_route} {'[OK]' if route_ok else '[FAIL]'}")
        print(f"     结果预览：{_preview_result(result)}")

        if route_ok:
            pass_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 70)
    print(f"测试结果：通过 {pass_count}/{len(TEST_CASES)}，失败 {fail_count}/{len(TEST_CASES)}")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()