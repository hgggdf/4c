"""OpenClaw集成测试脚本

用于测试OpenClaw统一入库接口的各种数据类型。
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"


def test_company_profile():
    """测试公司概况入库"""
    print("\n=== 测试公司概况入库 ===")

    data = {
        "batch_id": "20260425_0001",
        "task_id": "test_company_001",
        "source": {
            "source_type": "official_website",
            "source_name": "公司官网",
            "source_url": "https://example.com",
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
            "title": "公司简介",
            "publish_time": "2026-04-25T00:00:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test001",
            "raw_file_path": "/data/raw/company/600276/profile.html",
            "language": "zh"
        },
        "payload_type": "company_profile",
        "payload": {
            "business_summary": "主营医药研发与生产，专注创新药和高端仿制药",
            "core_products_json": ["抗肿瘤药", "麻醉药", "造影剂"],
            "main_segments_json": ["创新药", "仿制药", "原料药"],
            "market_position": "国内领先的医药企业，创新药研发实力强",
            "management_summary": "管理团队经验丰富，研发投入持续增长"
        },
        "processing": {
            "parse_status": "parsed",
            "parse_method": "html_extraction",
            "confidence_score": 0.95,
            "version_no": "v1"
        },
        "extra": {}
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_announcement_raw():
    """测试公告原始数据入库"""
    print("\n=== 测试公告原始数据入库 ===")

    data = {
        "batch_id": "20260425_0002",
        "task_id": "test_announcement_001",
        "source": {
            "source_type": "official_website",
            "source_name": "上海证券交易所",
            "source_url": "https://example.com/announcement/123",
            "source_category": "announcement"
        },
        "entity": {
            "entity_type": "company",
            "stock_code": "600276",
            "stock_name": "恒瑞医药"
        },
        "document": {
            "doc_type": "html",
            "title": "恒瑞医药关于新药获批的公告",
            "publish_time": "2026-04-25T00:00:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test002",
            "raw_file_path": "/data/raw/announcement/600276/20260425_001.html",
            "language": "zh"
        },
        "payload_type": "announcement_raw",
        "payload": {
            "announcement_type": "approval",
            "content": "本公司及董事会全体成员保证信息披露的内容真实、准确、完整，没有虚假记载、误导性陈述或重大遗漏。公司近日收到国家药品监督管理局核准签发的关于XX药品的《药品注册证书》...",
            "exchange": "SSE"
        },
        "processing": {
            "parse_status": "raw",
            "parse_method": "html",
            "confidence_score": 1.0,
            "version_no": "v1"
        },
        "extra": {}
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_financial_statement():
    """测试财务报表入库"""
    print("\n=== 测试财务报表入库（利润表） ===")

    data = {
        "batch_id": "20260425_0003",
        "task_id": "test_financial_001",
        "source": {
            "source_type": "annual_report",
            "source_name": "恒瑞医药2024年年度报告",
            "source_url": "https://example.com/report.pdf",
            "source_category": "financial_report"
        },
        "entity": {
            "entity_type": "company",
            "stock_code": "600276",
            "stock_name": "恒瑞医药"
        },
        "document": {
            "doc_type": "pdf",
            "title": "恒瑞医药2024年年度报告",
            "publish_time": "2025-04-19T00:00:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test003",
            "raw_file_path": "/data/raw/financial_report/600276/2024/report.pdf",
            "language": "zh"
        },
        "payload_type": "financial_statement",
        "payload": {
            "statement_type": "income_statement",
            "report_date": "2024-12-31",
            "revenue": 28500000000,
            "gross_profit": 23800000000,
            "net_profit": 6500000000,
            "net_profit_deducted": 6300000000,
            "operating_cost": 4700000000,
            "admin_expense": 1200000000,
            "selling_expense": 8500000000,
            "rd_expense": 5800000000,
            "operating_profit": 7200000000,
            "eps": 3.45
        },
        "processing": {
            "parse_status": "parsed",
            "parse_method": "pdf_table_extraction",
            "confidence_score": 0.96,
            "version_no": "v1"
        },
        "extra": {
            "fiscal_year": 2024,
            "report_type": "annual"
        }
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_drug_event():
    """测试药品事件入库"""
    print("\n=== 测试药品事件入库 ===")

    data = {
        "batch_id": "20260425_0004",
        "task_id": "test_drug_event_001",
        "source": {
            "source_type": "official_website",
            "source_name": "国家药监局",
            "source_url": "https://example.com/drug_approval/1",
            "source_category": "event"
        },
        "entity": {
            "entity_type": "company",
            "stock_code": "600276",
            "stock_name": "恒瑞医药"
        },
        "document": {
            "doc_type": "html",
            "title": "某药品获批上市",
            "publish_time": "2026-04-25T00:00:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test004",
            "raw_file_path": "/data/raw/event/approval_001.html",
            "language": "zh"
        },
        "payload_type": "drug_event",
        "payload": {
            "event_kind": "drug_approval",
            "drug_name": "卡瑞利珠单抗",
            "approval_type": "新药批准",
            "approval_date": "2026-04-25",
            "drug_stage": "approved",
            "market_scope": "national",
            "review_status": "approved",
            "is_innovative_drug": 1,
            "indication": "非小细胞肺癌"
        },
        "processing": {
            "parse_status": "cleaned",
            "parse_method": "llm_extraction",
            "confidence_score": 0.95,
            "version_no": "v1"
        },
        "extra": {}
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_news_raw():
    """测试新闻原始数据入库"""
    print("\n=== 测试新闻原始数据入库 ===")

    data = {
        "batch_id": "20260425_0005",
        "task_id": "test_news_001",
        "source": {
            "source_type": "news_site",
            "source_name": "东方财富资讯",
            "source_url": "https://example.com/news/789",
            "source_category": "news"
        },
        "entity": {
            "entity_type": "article"
        },
        "document": {
            "doc_type": "html",
            "title": "医药行业迎来政策利好",
            "publish_time": "2026-04-25T08:30:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test005",
            "raw_file_path": "/data/raw/news/20260425_001.html",
            "language": "zh"
        },
        "payload_type": "news_raw",
        "payload": {
            "news_uid": "eastmoney_test789",
            "content": "据悉，国家医保局近日发布新政策，将进一步支持创新药纳入医保目录，这对医药行业尤其是创新药企业构成重大利好...",
            "author_name": "记者张三",
            "news_type": "policy"
        },
        "processing": {
            "parse_status": "raw",
            "parse_method": "html",
            "confidence_score": 1.0,
            "version_no": "v1"
        },
        "extra": {}
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_macro_indicator():
    """测试宏观指标入库"""
    print("\n=== 测试宏观指标入库 ===")

    data = {
        "batch_id": "20260425_0006",
        "task_id": "test_macro_001",
        "source": {
            "source_type": "gov_site",
            "source_name": "国家统计局",
            "source_url": "https://example.com/cpi",
            "source_category": "macro"
        },
        "entity": {
            "entity_type": "macro"
        },
        "document": {
            "doc_type": "html",
            "title": "2026年3月居民消费价格指数",
            "publish_time": "2026-04-10T09:00:00+08:00",
            "crawl_time": "2026-04-25T10:20:00+08:00",
            "file_hash": "sha256:test006",
            "raw_file_path": "/data/raw/macro/202603_cpi.html",
            "language": "zh"
        },
        "payload_type": "macro_indicator",
        "payload": {
            "indicator_name": "居民消费价格指数",
            "period": "2026-03",
            "value": 101.2,
            "unit": "同比%"
        },
        "processing": {
            "parse_status": "parsed",
            "parse_method": "html_table_extraction",
            "confidence_score": 0.97,
            "version_no": "v1"
        },
        "extra": {
            "region": "全国"
        }
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_stock_daily():
    """测试股票日行情入库"""
    print("\n=== 测试股票日行情入库 ===")

    data = {
        "batch_id": "20260425_0007",
        "task_id": "test_stock_daily_001",
        "source": {
            "source_type": "market_data",
            "source_name": "交易所行情",
            "source_url": "https://example.com/quote",
            "source_category": "stock_daily"
        },
        "entity": {
            "entity_type": "company",
            "stock_code": "600276",
            "stock_name": "恒瑞医药"
        },
        "document": {
            "doc_type": "json",
            "title": "600276日行情",
            "publish_time": "2026-04-25T15:00:00+08:00",
            "crawl_time": "2026-04-25T15:05:00+08:00",
            "file_hash": "sha256:test007",
            "raw_file_path": "/data/raw/stock_daily/600276/20260425.json",
            "language": "zh"
        },
        "payload_type": "stock_daily",
        "payload": {
            "trade_date": "2026-04-25",
            "open_price": 45.20,
            "close_price": 46.50,
            "high_price": 47.00,
            "low_price": 45.00,
            "volume": 12345678,
            "turnover": 567890123.45
        },
        "processing": {
            "parse_status": "parsed",
            "parse_method": "json_extraction",
            "confidence_score": 1.0,
            "version_no": "v1"
        },
        "extra": {}
    }

    response = requests.post(f"{BASE_URL}/api/openclaw/ingest", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def main():
    """运行所有测试"""
    print("=" * 60)
    print("OpenClaw 统一入库接口测试")
    print("=" * 60)

    tests = [
        ("公司概况", test_company_profile),
        ("公告原始数据", test_announcement_raw),
        ("财务报表", test_financial_statement),
        ("药品事件", test_drug_event),
        ("新闻原始数据", test_news_raw),
        ("宏观指标", test_macro_indicator),
        ("股票日行情", test_stock_daily),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n错误: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{name}: {status}")

    success_count = sum(1 for _, success in results if success)
    print(f"\n总计: {success_count}/{len(results)} 个测试通过")


if __name__ == "__main__":
    main()
