"""直接调用 service 接口测试全部 13 种 payload_type"""
import sys, os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, '.')

from app.service.container import ServiceContainer
from app.service.write_requests import (
    UpsertCompanyMasterRequest, UpsertCompanyProfileRequest,
    IngestAnnouncementPackageRequest, IngestNewsPackageRequest,
    IngestFinancialPackageRequest,
)

c = ServiceContainer.build_default()
results = {}

# 1. company_master
r = c.company_write.upsert_company_master(UpsertCompanyMasterRequest(
    stock_code='600276', stock_name='恒瑞医药',
    industry_level1='IND_MED_01', industry_level2='医药制造',
    source_type='test', source_url='https://test.com',
))
results['company_master'] = (r.success, r.message)

# 2. company_profile
r = c.company_write.upsert_company_profile(UpsertCompanyProfileRequest(
    stock_code='600276', business_summary='测试公司概况', sync_vector_index=False,
))
results['company_profile'] = (r.success, r.message)

# 3. announcement_raw
r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    raw_announcements=[{
        'stock_code': '600276', 'title': '测试公告', 'publish_date': '2026-04-25',
        'announcement_type': 'test', 'exchange': 'SSE', 'content': '测试内容',
        'source_url': 'https://test.com', 'source_type': 'test', 'file_hash': 'test_ann_raw_2',
    }],
    sync_vector_index=False,
))
results['announcement_raw'] = (r.success, r.message)

# 4. announcement_structured (需要先有 raw announcement 的 id)
# 从 announcement_raw 结果里取 id
ann_raw_id = None
r_raw = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    raw_announcements=[{
        'stock_code': '600276', 'title': '结构化测试公告', 'publish_date': '2026-04-25',
        'announcement_type': 'test', 'exchange': 'SSE', 'content': '测试内容',
        'source_url': 'https://test.com', 'source_type': 'test', 'file_hash': 'test_ann_for_struct',
    }],
    sync_vector_index=False,
))
if r_raw.success and r_raw.data:
    ids = r_raw.data.get('raw_announcements', {}).get('ids', [])
    if ids:
        ann_raw_id = ids[0]

r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    structured_announcements=[{
        'announcement_id': ann_raw_id,
        'stock_code': '600276', 'category': 'test', 'summary_text': '测试摘要',
        'key_fields_json': None, 'signal_type': 'neutral', 'risk_level': 'low',
    }],
))
results['announcement_structured'] = (r.success, r.message)

# 5. news_raw
r = c.ingest.ingest_news_package(IngestNewsPackageRequest(
    news_raw=[{
        'news_uid': 'test_news_002', 'title': '测试新闻', 'publish_time': '2026-04-25T00:00:00',
        'source_name': 'test', 'source_url': 'https://test.com', 'author_name': 'test',
        'content': '测试新闻内容', 'news_type': 'general', 'language': 'zh', 'file_hash': 'test_news_raw_2',
    }],
    sync_vector_index=False,
))
results['news_raw'] = (r.success, r.message)

# 6. news_structured
r = c.ingest.ingest_news_package(IngestNewsPackageRequest(
    news_structured=[{
        'topic_category': 'pharma', 'summary_text': '测试新闻摘要',
        'keywords_json': None, 'signal_type': 'positive', 'impact_level': 'medium',
        'impact_horizon': 'short', 'sentiment_label': 'positive', 'confidence_score': 0.9,
    }],
))
results['news_structured'] = (r.success, r.message)

# 7. financial_statement (income)
r = c.ingest.ingest_financial_package(IngestFinancialPackageRequest(
    income_statements=[{
        'stock_code': '600276', 'report_date': '2025-12-31', 'fiscal_year': 2025,
        'report_type': 'annual', 'source_type': 'test', 'source_url': 'https://test.com',
        'revenue': 27000000000, 'operating_cost': 5000000000, 'gross_profit': 22000000000,
        'net_profit': 6000000000, 'eps': 2.5,
    }],
))
results['financial_statement_income'] = (r.success, r.message)

# 8. financial_metric
r = c.ingest.ingest_financial_package(IngestFinancialPackageRequest(
    financial_metrics=[{
        'stock_code': '600276', 'report_date': '2025-12-31', 'fiscal_year': 2025,
        'metric_name': 'ROE', 'metric_value': 0.18, 'metric_unit': '%',
        'calc_method': 'standard', 'source_ref_json': None,
    }],
))
results['financial_metric'] = (r.success, r.message)

# 9. macro_indicator
r = c.ingest.ingest_news_package(IngestNewsPackageRequest(
    macro_indicators=[{
        'indicator_name': 'CPI', 'period': '2026-03', 'value': 0.5,
        'unit': '%', 'source_type': 'test', 'source_url': 'https://test.com',
    }],
))
results['macro_indicator'] = (r.success, r.message)

# 10. drug_approval
r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    drug_approvals=[{
        'stock_code': '600276', 'drug_name': '测试药物', 'approval_type': 'NDA',
        'approval_date': '2026-04-01', 'indication': '测试适应症', 'drug_stage': 'approved',
        'is_innovative_drug': 1, 'review_status': 'approved', 'market_scope': 'China',
        'source_announcement_id': None, 'source_type': 'test', 'source_url': 'https://test.com',
    }],
))
results['drug_approval'] = (r.success, r.message)

# 11. procurement_event
r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    procurement_events=[{
        'stock_code': '600276', 'drug_name': '测试药物', 'procurement_round': '第九批',
        'bid_result': 'won', 'price_change_ratio': -0.3, 'event_date': '2026-04-01',
        'impact_summary': '中标', 'source_announcement_id': None,
        'source_type': 'test', 'source_url': 'https://test.com',
    }],
))
results['procurement_event'] = (r.success, r.message)

# 12. trial_event
r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    clinical_trials=[{
        'stock_code': '600276', 'drug_name': '测试药物', 'trial_phase': 'Phase3',
        'event_type': 'enrollment_complete', 'event_date': '2026-04-01',
        'indication': '测试适应症', 'summary_text': '三期临床完成入组',
        'source_announcement_id': None, 'source_type': 'test', 'source_url': 'https://test.com',
    }],
))
results['trial_event'] = (r.success, r.message)

# 13. regulatory_risk_event
r = c.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
    regulatory_risks=[{
        'stock_code': '600276', 'risk_type': 'inspection', 'event_date': '2026-04-01',
        'risk_level': 'medium', 'summary_text': '监管检查',
        'source_announcement_id': None, 'source_type': 'test', 'source_url': 'https://test.com',
    }],
))
results['regulatory_risk_event'] = (r.success, r.message)

# 14. stock_daily
r = c.ingest.ingest_financial_package(IngestFinancialPackageRequest(
    stock_daily=[{
        'stock_code': '600276', 'trade_date': '2026-04-25',
        'open_price': 50.0, 'close_price': 51.0, 'high_price': 52.0, 'low_price': 49.0,
        'volume': 1000000, 'turnover': 51000000, 'source_type': 'test',
    }],
))
results['stock_daily'] = (r.success, r.message)

print()
print('=' * 50)
all_pass = True
for name, (success, msg) in results.items():
    status = 'PASS' if success else 'FAIL'
    if not success:
        all_pass = False
    print(f'[{status}] {name}: {msg if not success else "OK"}')
print('=' * 50)
print('全部通过' if all_pass else '有失败项，请检查上方 FAIL 条目')
