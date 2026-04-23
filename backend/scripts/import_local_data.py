"""直接从本地 dataset.json 解析并写入数据库"""

import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.staging.local_company_data_store import LocalCompanyDataStore
from app.service.container import ServiceContainer
from app.service.write_requests import (
    UpsertCompanyMasterRequest,
    IngestFinancialPackageRequest,
    IngestAnnouncementPackageRequest,
)


# ── 字段映射 ──────────────────────────────────────────────

def _date(val) -> str | None:
    if not val:
        return None
    s = str(val).strip()[:10]
    return s if len(s) == 10 else None


def _float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _parse_income(row: dict, stock_code: str) -> dict | None:
    rd = _date(row.get("REPORT_DATE"))
    if not rd:
        return None
    revenue = _float(row.get("TOTAL_OPERATE_INCOME") or row.get("OPERATE_INCOME"))
    if revenue is None:
        return None
    return {
        "stock_code": stock_code,
        "report_date": rd,
        "fiscal_year": int(rd[:4]),
        "report_type": str(row.get("REPORT_TYPE") or ""),
        "revenue": revenue,
        "operating_cost": _float(row.get("OPERATE_COST")),
        "gross_profit": (revenue - (_float(row.get("OPERATE_COST")) or 0)) if revenue else None,
        "selling_expense": _float(row.get("SALE_EXPENSE")),
        "admin_expense": _float(row.get("MANAGE_EXPENSE")),
        "rd_expense": _float(row.get("RESEARCH_EXPENSE") or row.get("ME_RESEARCH_EXPENSE")),
        "operating_profit": _float(row.get("OPERATE_PROFIT")),
        "net_profit": _float(row.get("PARENT_NETPROFIT") or row.get("NETPROFIT")),
        "net_profit_deducted": _float(row.get("DEDUCT_PARENT_NETPROFIT")),
        "eps": _float(row.get("BASIC_EPS")),
        "source_type": "local_import",
    }


def _parse_balance(row: dict, stock_code: str) -> dict | None:
    rd = _date(row.get("REPORT_DATE"))
    if not rd:
        return None
    total_assets = _float(row.get("TOTAL_ASSETS"))
    if total_assets is None:
        return None
    return {
        "stock_code": stock_code,
        "report_date": rd,
        "fiscal_year": int(rd[:4]),
        "report_type": str(row.get("REPORT_TYPE") or ""),
        "total_assets": total_assets,
        "total_liabilities": _float(row.get("TOTAL_LIABILITIES")),
        "accounts_receivable": _float(row.get("ACCOUNTS_RECE")),
        "inventory": _float(row.get("INVENTORY")),
        "cash": _float(row.get("MONETARYFUNDS")),
        "equity": _float(row.get("TOTAL_EQUITY") or row.get("PARENT_EQUITY")),
        "goodwill": _float(row.get("GOODWILL")),
        "source_type": "local_import",
    }


def _parse_cashflow(row: dict, stock_code: str) -> dict | None:
    rd = _date(row.get("REPORT_DATE"))
    if not rd:
        return None
    op_cf = _float(row.get("NETCASH_OPERATE"))
    if op_cf is None:
        return None
    inv_cf = _float(row.get("NETCASH_INVEST"))
    fin_cf = _float(row.get("NETCASH_FINANCE"))
    capex = _float(row.get("CONSTRUCT_LONG_ASSET") or row.get("BUY_FIXED_ASSET"))
    free_cf = (op_cf - abs(capex)) if (op_cf is not None and capex is not None) else None
    return {
        "stock_code": stock_code,
        "report_date": rd,
        "fiscal_year": int(rd[:4]),
        "report_type": str(row.get("REPORT_TYPE") or ""),
        "operating_cashflow": op_cf,
        "investing_cashflow": inv_cf,
        "financing_cashflow": fin_cf,
        "free_cashflow": free_cf,
        "source_type": "local_import",
    }


def _parse_metrics(income_rows: list[dict], balance_rows: list[dict], stock_code: str) -> list[dict]:
    """从利润表和资产负债表计算关键财务指标"""
    metrics = []
    balance_by_date = {_date(r.get("REPORT_DATE")): r for r in balance_rows if _date(r.get("REPORT_DATE"))}

    for row in income_rows:
        rd = _date(row.get("REPORT_DATE"))
        if not rd:
            continue
        revenue = _float(row.get("TOTAL_OPERATE_INCOME") or row.get("OPERATE_INCOME"))
        cost = _float(row.get("OPERATE_COST"))
        net_profit = _float(row.get("PARENT_NETPROFIT") or row.get("NETPROFIT"))
        rd_expense = _float(row.get("RESEARCH_EXPENSE") or row.get("ME_RESEARCH_EXPENSE"))
        fy = int(rd[:4])

        if revenue and cost is not None:
            metrics.append({"stock_code": stock_code, "report_date": rd, "fiscal_year": fy,
                             "metric_name": "gross_margin", "metric_value": round((revenue - cost) / revenue, 4),
                             "metric_unit": "%", "calc_method": "auto"})
        if revenue and net_profit is not None:
            metrics.append({"stock_code": stock_code, "report_date": rd, "fiscal_year": fy,
                             "metric_name": "net_margin", "metric_value": round(net_profit / revenue, 4),
                             "metric_unit": "%", "calc_method": "auto"})
        if revenue and rd_expense is not None:
            metrics.append({"stock_code": stock_code, "report_date": rd, "fiscal_year": fy,
                             "metric_name": "rd_ratio", "metric_value": round(rd_expense / revenue, 4),
                             "metric_unit": "%", "calc_method": "auto"})

        bal = balance_by_date.get(rd)
        if bal and net_profit is not None:
            equity = _float(bal.get("TOTAL_EQUITY") or bal.get("PARENT_EQUITY"))
            if equity and equity > 0:
                metrics.append({"stock_code": stock_code, "report_date": rd, "fiscal_year": fy,
                                 "metric_name": "roe", "metric_value": round(net_profit / equity, 4),
                                 "metric_unit": "%", "calc_method": "auto"})
            total_assets = _float(bal.get("TOTAL_ASSETS"))
            total_liab = _float(bal.get("TOTAL_LIABILITIES"))
            if total_assets and total_liab is not None:
                metrics.append({"stock_code": stock_code, "report_date": rd, "fiscal_year": fy,
                                 "metric_name": "debt_ratio", "metric_value": round(total_liab / total_assets, 4),
                                 "metric_unit": "%", "calc_method": "auto"})
    return metrics


def _parse_announcements(rows: list[dict], stock_code: str) -> list[dict]:
    result = []
    for row in rows:
        title = str(
            row.get("公告标题") or row.get("title") or row.get("TITLE") or row.get("ann_title") or ""
        ).strip()
        if not title:
            continue
        pub_date = _date(
            row.get("公告日期") or row.get("notice_date") or row.get("NOTICE_DATE")
            or row.get("ann_date") or row.get("date")
        )
        if not pub_date:
            continue
        result.append({
            "stock_code": stock_code,
            "title": title,
            "publish_date": pub_date,
            "announcement_type": str(row.get("公告类型") or row.get("ann_type") or row.get("type") or ""),
            "exchange": str(row.get("exchange") or ""),
            "content": str(row.get("content") or row.get("CONTENT") or ""),
            "source_url": str(row.get("网址") or row.get("url") or row.get("URL") or ""),
            "source_type": "local_import",
        })
    return result


# ── 主导入逻辑 ────────────────────────────────────────────

def import_company(stock_code: str, container, limit: int = 20) -> bool:
    store = LocalCompanyDataStore()
    dataset = store.load_company_dataset(stock_code)
    if not dataset:
        print(f"  [SKIP] 无本地数据: {stock_code}")
        return False

    stock_name = str(dataset.get("name") or stock_code).strip()
    company_info = dataset.get("company_info") or {}
    full_name = str(company_info.get("股票名称") or company_info.get("公司名称") or "").strip() or None
    exchange = str(dataset.get("exchange") or "").strip() or None
    aliases = dataset.get("aliases") or None

    # 1. 公司基本信息
    r = container.company_write.upsert_company_master(UpsertCompanyMasterRequest(
        stock_code=stock_code, stock_name=stock_name, full_name=full_name,
        exchange=exchange, alias_json=aliases, status="active", source_type="local_import",
    ))
    if not r.success:
        print(f"  [FAIL] company_master: {r.message}")
        return False
    print(f"  [OK] company_master: {stock_name}")

    # 2. 财务数据
    profit_rows  = dataset.get("profit_sheet", [])[:limit]
    balance_rows = dataset.get("balance_sheet", [])[:limit]
    cf_rows      = dataset.get("cash_flow_sheet", [])[:limit]

    income_stmts  = [x for x in (_parse_income(r, stock_code)  for r in profit_rows)  if x]
    balance_stmts = [x for x in (_parse_balance(r, stock_code) for r in balance_rows) if x]
    cf_stmts      = [x for x in (_parse_cashflow(r, stock_code) for r in cf_rows)     if x]
    metrics       = _parse_metrics(profit_rows, balance_rows, stock_code)

    r = container.ingest.ingest_financial_package(IngestFinancialPackageRequest(
        income_statements=income_stmts,
        balance_sheets=balance_stmts,
        cashflow_statements=cf_stmts,
        financial_metrics=metrics,
        sync_vector_index=False,
    ))
    if not r.success:
        print(f"  [FAIL] financial: {r.message}")
    else:
        print(f"  [OK] financial: 利润表{len(income_stmts)}期 / 资产负债表{len(balance_stmts)}期 / 现金流{len(cf_stmts)}期 / 指标{len(metrics)}条")

    # 3. 公告
    ann_rows = dataset.get("announcements", [])[:limit * 5]
    raw_anns = _parse_announcements(ann_rows, stock_code)
    if raw_anns:
        r = container.ingest.ingest_announcement_package(IngestAnnouncementPackageRequest(
            raw_announcements=raw_anns,
            sync_vector_index=False,
        ))
        if not r.success:
            print(f"  [FAIL] announcements: {r.message}")
        else:
            print(f"  [OK] announcements: {len(raw_anns)} 条")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="从本地 dataset.json 导入公司数据")
    parser.add_argument("stock_codes", nargs="*", help="股票代码，不填则导入全部")
    parser.add_argument("--limit", type=int, default=20, help="每家公司财务数据期数上限（默认20）")
    args = parser.parse_args()

    store = LocalCompanyDataStore()
    if args.stock_codes:
        codes = args.stock_codes
    else:
        codes = [f.parent.name for f in store.list_dataset_files()]

    print(f"准备导入 {len(codes)} 家公司，每家财务数据最多 {args.limit} 期\n")
    container = ServiceContainer.build_default()

    ok, fail = 0, 0
    for code in codes:
        print(f"\n[{code}]")
        try:
            if import_company(code, container, limit=args.limit):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            fail += 1

    print(f"\n完成: 成功 {ok} 家 / 失败 {fail} 家")


if __name__ == "__main__":
    main()
