"""
管线数据查询接口 mock 实现。
联调时由他替换为真实 repository 调用，此文件整体删除。

接口约定：
  get_pipeline_drugs(stock_code: str) -> list[dict]
  字段：drug_name, indication, trial_phase, route_of_administration, expected_approval_year
  缺失字段返回 None，不省略 key。
"""

from __future__ import annotations

_MOCK_DATA: dict[str, list[dict]] = {
    "600276": [  # 恒瑞医药
        {
            "drug_name": "SHR-1314",
            "indication": "特应性皮炎",
            "trial_phase": "phase3",
            "route_of_administration": "注射",
            "expected_approval_year": 2027,
        },
        {
            "drug_name": "HLX10",
            "indication": "非小细胞肺癌",
            "trial_phase": "phase3",
            "route_of_administration": "注射",
            "expected_approval_year": 2026,
        },
    ],
    "000538": [  # 云南白药
        {
            "drug_name": "云南白药气雾剂新适应症",
            "indication": "骨关节炎",
            "trial_phase": "phase2",
            "route_of_administration": "口服",
            "expected_approval_year": None,
        },
    ],
    "DEFAULT": [
        {
            "drug_name": "在研药品A",
            "indication": "未知适应症",
            "trial_phase": "phase2",
            "route_of_administration": None,
            "expected_approval_year": None,
        },
    ],
}


def get_pipeline_drugs(stock_code: str) -> list[dict]:
    """返回股票代码对应的管线列表，使用 mock 数据。"""
    return _MOCK_DATA.get(stock_code, _MOCK_DATA["DEFAULT"])
