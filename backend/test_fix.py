#!/usr/bin/env python
"""简单测试脚本 - 测试修复后的接口"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# 测试数据
data = {
    "batch_id": "20260425_fix_test",
    "task_id": "test_fix",
    "source": {
        "source_type": "test",
        "source_name": "test",
        "source_url": "https://test.com",
        "source_category": "company"
    },
    "entity": {
        "entity_type": "company",
        "stock_code": "600276",
        "stock_name": "恒瑞医药",
        "industry_code": "IND_MED_01",
        "industry_name": "医药制造"
    },
    "document": {
        "doc_type": "html",
        "title": "测试",
        "publish_time": "2026-04-25T00:00:00+08:00",
        "crawl_time": "2026-04-25T00:00:00+08:00",
        "file_hash": "test_fix",
        "raw_file_path": "/test",
        "language": "zh"
    },
    "payload_type": "company_profile",
    "payload": {
        "business_summary": "测试公司概况修复"
    },
    "processing": {
        "parse_status": "parsed",
        "parse_method": "test",
        "confidence_score": 1.0,
        "version_no": "v1"
    },
    "extra": {}
}

print("测试 OpenClaw 接口修复...")
print("=" * 60)

try:
    response = requests.post(
        f"{BASE_URL}/api/openclaw/ingest",
        json=data,
        timeout=10
    )

    print(f"状态码: {response.status_code}")
    print(f"响应:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("\n✓ 测试成功！")
        else:
            print(f"\n✗ 测试失败: {result.get('message')}")
    else:
        print(f"\n✗ HTTP 错误: {response.status_code}")

except Exception as e:
    print(f"\n✗ 请求失败: {e}")
