"""快速导入本地公司数据到数据库的脚本"""

import sys
from pathlib import Path

# 确保可以导入项目模块
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.staging.local_company_data_store import LocalCompanyDataStore
from crawler.pipelines.financial_pipeline import build_financial_package_payload
from app.service.container import ServiceContainer
from app.service.write_requests import (
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    UpsertCompanyMasterRequest,
)


def import_company_data(stock_code: str):
    """导入单个公司的数据"""
    print(f"\n{'='*60}")
    print(f"导入 {stock_code} 的数据")
    print(f"{'='*60}")

    # 1. 加载本地数据
    print(f"[1/4] 加载本地数据...")
    store = LocalCompanyDataStore()
    dataset = store.load_company_dataset(stock_code)

    if not dataset:
        print(f"  ✗ 未找到 {stock_code} 的本地数据")
        return False

    print(f"  ✓ 数据加载成功")
    print(f"    - 公告: {len(dataset.get('announcements', []))} 条")
    print(f"    - 研报: {len(dataset.get('research_reports', []))} 篇")
    print(f"    - 新闻: {len(dataset.get('news', []))} 条")
    print(f"    - 财务数据: {len(dataset.get('financial_abstract', []))} 期")

    # 2. 创建服务容器
    print(f"\n[2/4] 初始化服务...")
    container = ServiceContainer.build_default()
    print(f"  ✓ 服务容器创建成功")

    # 3. 写入公司基本信息
    print(f"\n[3/4] 写入公司基本信息...")
    company_info = dataset.get("company_info") or {}
    stock_name = str(dataset.get("name") or stock_code).strip() or stock_code
    full_name = str(company_info.get("股票名称") or company_info.get("公司名称") or "").strip() or None
    exchange = str(dataset.get("exchange") or "").strip() or None
    aliases = dataset.get("aliases") or None

    master_req = UpsertCompanyMasterRequest(
        stock_code=stock_code,
        stock_name=stock_name,
        full_name=full_name,
        exchange=exchange,
        alias_json=aliases,
        status="active",
        source_type="local_import",
    )

    result = container.company_write.upsert_company_master(master_req)
    if not result.success:
        print(f"  ✗ 公司信息写入失败: {result.message}")
        return False

    print(f"  ✓ 公司信息写入成功: {stock_name}")

    # 4. 写入财务数据（限制数量避免超时）
    print(f"\n[4/4] 写入财务数据...")

    # 限制数据量
    limited_dataset = {
        **dataset,
        'announcements': dataset.get('announcements', [])[:50],  # 只导入最近50条公告
        'research_reports': dataset.get('research_reports', [])[:20],  # 只导入最近20篇研报
        'news': dataset.get('news', [])[:20],  # 只导入最近20条新闻
        'financial_abstract': dataset.get('financial_abstract', [])[:20],  # 只导入最近20期财务数据
        'balance_sheet': dataset.get('balance_sheet', [])[:20],
        'profit_sheet': dataset.get('profit_sheet', [])[:20],
        'cash_flow_sheet': dataset.get('cash_flow_sheet', [])[:20],
        'main_business': dataset.get('main_business', [])[:50],
    }

    print(f"  限制数据量（避免超时）:")
    print(f"    - 公告: {len(limited_dataset.get('announcements', []))} 条")
    print(f"    - 研报: {len(limited_dataset.get('research_reports', []))} 篇")
    print(f"    - 新闻: {len(limited_dataset.get('news', []))} 条")
    print(f"    - 财务数据: {len(limited_dataset.get('financial_abstract', []))} 期")

    # 构建财务数据包
    payload = build_financial_package_payload(
        limited_dataset,
        stock_code,
        sync_vector_index=False  # 先不同步向量索引，加快速度
    )

    financial_req = IngestFinancialPackageRequest(
        income_statements=payload.get("income_statements", []),
        balance_sheets=payload.get("balance_sheets", []),
        cashflow_statements=payload.get("cashflow_statements", []),
        financial_metrics=payload.get("financial_metrics", []),
        financial_notes=payload.get("financial_notes", []),
        business_segments=payload.get("business_segments", []),
        sync_vector_index=False,
    )

    result = container.ingest.ingest_financial_package(financial_req)
    if not result.success:
        print(f"  ✗ 财务数据写入失败: {result.message}")
        return False

    print(f"  ✓ 财务数据写入成功")
    print(f"    - 利润表: {len(payload.get('income_statements', []))} 期")
    print(f"    - 资产负债表: {len(payload.get('balance_sheets', []))} 期")
    print(f"    - 现金流量表: {len(payload.get('cashflow_statements', []))} 期")
    print(f"    - 财务指标: {len(payload.get('financial_metrics', []))} 条")
    print(f"    - 业务分部: {len(payload.get('business_segments', []))} 条")

    print(f"\n{'='*60}")
    print(f"✓ {stock_code} {stock_name} 导入完成")
    print(f"{'='*60}")

    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="快速导入本地公司数据到数据库")
    parser.add_argument("stock_codes", nargs="+", help="股票代码列表，如 600276 600519")
    args = parser.parse_args()

    success_count = 0
    fail_count = 0

    for stock_code in args.stock_codes:
        try:
            if import_company_data(stock_code):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"\n✗ {stock_code} 导入失败: {e}")
            fail_count += 1

    print(f"\n\n{'='*60}")
    print(f"导入完成")
    print(f"{'='*60}")
    print(f"成功: {success_count} 家")
    print(f"失败: {fail_count} 家")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
