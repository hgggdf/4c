"""
检索准确性测试：覆盖结构化、非结构化、混合三类查询
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy.orm import Session
from database.session import engine
from data.retriever import route_query, search_structured, search_unstructured, hybrid_search

TEST_CASES = [
    # (问题, 期望路由类型, 期望结果包含关键词)
    ("恒瑞医药2024年毛利率是多少",          "structured",   ["恒瑞医药", "毛利率", "86"]),
    ("药明康德2023年净利润",                 "structured",   ["药明康德", "净利润", "96"]),
    ("爱尔眼科2022年ROE",                    "structured",   ["爱尔眼科", "ROE", "19"]),
    ("对比三家公司2024年毛利率",             "structured",   ["毛利率"]),
    ("恒瑞医药近三年营业总收入趋势",         "structured",   ["恒瑞医药", "营业总收入"]),
    ("CPI和GDP宏观数据",                     "structured",   ["CPI", "GDP"]),
    ("恒瑞医药的研发管线分析",               "unstructured", ["恒瑞", "研发"]),
    ("药明康德集采风险和投资价值",           "unstructured", ["药明康德"]),
    ("医药行业政策对CXO的影响",              "unstructured", ["CXO", "医药"]),
    ("恒瑞医药2023年毛利率多少，以及行业风险", "hybrid",    ["恒瑞医药", "毛利率"]),
]


def run_tests() -> None:
    print("=" * 70)
    print("检索准确性测试")
    print("=" * 70)

    pass_count = 0
    fail_count = 0

    with Session(engine) as db:
        for i, (query, expected_route, expected_keywords) in enumerate(TEST_CASES, 1):
            print(f"\n[{i:02d}] 问题：{query}")

            # 测试路由
            actual_route = route_query(query)
            route_ok = actual_route == expected_route
            print(f"     路由：期望={expected_route}，实际={actual_route} {'[OK]' if route_ok else '[FAIL]'}")

            # 执行检索
            if actual_route == "structured":
                result = search_structured(db, query)
            elif actual_route == "unstructured":
                result = search_unstructured(query, top_k=2)
            else:
                s, u = hybrid_search(db, query)
                result = "\n".join(filter(None, [s, u]))

            if result:
                # 检查关键词命中
                hits = [kw for kw in expected_keywords if kw in result]
                kw_ok = len(hits) >= len(expected_keywords) // 2 + 1
                print(f"     关键词命中：{hits}/{expected_keywords} {'[OK]' if kw_ok else '[WARN]'}")
                print(f"     结果预览：{result[:120].replace(chr(10), ' ')}")
                if route_ok and kw_ok:
                    pass_count += 1
                else:
                    fail_count += 1
            else:
                print(f"     结果：空 [FAIL]")
                fail_count += 1

    print("\n" + "=" * 70)
    print(f"测试结果：通过 {pass_count}/{len(TEST_CASES)}，失败 {fail_count}/{len(TEST_CASES)}")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
