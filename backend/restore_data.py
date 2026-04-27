"""
从 local_data/pharma_companies/*/dataset.json 重新导入所有数据到当前数据库。
"""

import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database.session import SessionLocal
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from sqlalchemy.dialects.mysql import insert as mysql_insert

DATA_DIR = BACKEND_ROOT / "local_data" / "pharma_companies"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _str(v) -> str:
    return str(v).strip() if v else ""


def _float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _date(v) -> str | None:
    if not v:
        return None
    s = str(v).strip()[:10]
    return s if len(s) == 10 else None


def _uid(stock_code: str, suffix: str) -> str:
    return hashlib.md5(f"{stock_code}:{suffix}".encode()).hexdigest()[:32]


def import_company(db, stock_code: str, data: dict):
    info = data.get("company_info") or {}
    name = _str(data.get("name") or info.get("stock_name") or stock_code)
    row = {
        "stock_code": stock_code,
        "stock_name": name,
        "full_name": _str(info.get("full_name")),
        "exchange": _str(data.get("exchange")),
        "business_summary": _str(info.get("business_summary") or info.get("profile")),
    }
    stmt = mysql_insert(Company).values(**row)
    stmt = stmt.on_duplicate_key_update(
        stock_name=row["stock_name"],
        full_name=row["full_name"],
        exchange=row["exchange"],
        business_summary=row["business_summary"],
    )
    db.execute(stmt)


def import_financials(db, stock_code: str, data: dict):
    rows = data.get("profit_sheet") or []
    count = 0
    for r in rows:
        rd = _date(r.get("REPORT_DATE"))
        if not rd:
            continue
        revenue = _float(r.get("TOTAL_OPERATE_INCOME") or r.get("OPERATE_INCOME"))
        net_profit = _float(r.get("PARENT_NETPROFIT") or r.get("NETPROFIT"))
        if revenue is None and net_profit is None:
            continue
        operating_cost = _float(r.get("OPERATE_COST"))
        gross_profit = (revenue - operating_cost) if (revenue and operating_cost) else None
        gross_margin = (gross_profit / revenue) if (gross_profit and revenue) else None
        rd_expense = _float(r.get("RESEARCH_EXPENSE") or r.get("ME_RESEARCH_EXPENSE"))
        rd_ratio = (rd_expense / revenue) if (rd_expense and revenue) else None
        row = {
            "stock_code": stock_code,
            "report_date": rd,
            "fiscal_year": int(rd[:4]),
            "report_type": _str(r.get("REPORT_TYPE") or "季报")[:32],
            "revenue": revenue,
            "operating_cost": operating_cost,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
            "selling_expense": _float(r.get("SALE_EXPENSE")),
            "admin_expense": _float(r.get("MANAGE_EXPENSE")),
            "rd_expense": rd_expense,
            "rd_ratio": rd_ratio,
            "operating_profit": _float(r.get("OPERATE_PROFIT")),
            "net_profit": net_profit,
            "net_profit_deducted": _float(r.get("DEDUCT_PARENT_NETPROFIT")),
            "eps": _float(r.get("BASIC_EPS")),
        }
        stmt = mysql_insert(FinancialHot).values(**row)
        stmt = stmt.on_duplicate_key_update(
            revenue=row["revenue"],
            net_profit=row["net_profit"],
            gross_margin=row["gross_margin"],
            rd_ratio=row["rd_ratio"],
        )
        db.execute(stmt)
        count += 1
    return count


def import_announcements(db, stock_code: str, data: dict):
    rows = data.get("announcements") or []
    count = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        keys = list(r.keys())
        # dataset.json 里公告字段可能是中文key，按位置取
        # keys: [股票代码, 股票名称, 公告标题, 公告类型, 公告日期, 链接]
        def _get(key_candidates, pos=None):
            for k in key_candidates:
                if k in r:
                    return r[k]
            if pos is not None and len(keys) > pos:
                return r.get(keys[pos])
            return ""

        title = _str(_get(["title", "announcement_title"], 2))
        ann_type = _str(_get(["announcement_type", "type"], 3))
        pub_date = _date(_get(["publish_date", "date", "announcement_date"], 4))
        url = _str(_get(["url", "source_url", "link"], 5))

        if not title or not pub_date:
            continue

        uid = _uid(stock_code, f"{pub_date}:{title[:50]}")
        row = {
            "announcement_uid": uid,
            "stock_code": stock_code,
            "title": title[:500],
            "publish_date": pub_date,
            "announcement_type": ann_type[:64],
            "source_url": url[:512],
            "content": "",
        }
        stmt = mysql_insert(AnnouncementHot).values(**row)
        stmt = stmt.on_duplicate_key_update(
            title=row["title"],
            announcement_type=row["announcement_type"],
            source_url=row["source_url"],
        )
        db.execute(stmt)
        count += 1
    return count


def main():
    companies = sorted(DATA_DIR.iterdir()) if DATA_DIR.exists() else []
    if not companies:
        log(f"ERROR: 找不到数据目录 {DATA_DIR}")
        return

    log(f"找到 {len(companies)} 家公司，开始导入...")
    total_fin = total_ann = 0

    with SessionLocal() as db:
        for company_dir in companies:
            dataset_path = company_dir / "dataset.json"
            if not dataset_path.exists():
                continue
            stock_code = company_dir.name
            try:
                with open(dataset_path, encoding="utf-8") as f:
                    data = json.load(f)

                import_company(db, stock_code, data)
                fin_count = import_financials(db, stock_code, data)
                ann_count = import_announcements(db, stock_code, data)
                db.commit()
                total_fin += fin_count
                total_ann += ann_count
                log(f"  {stock_code} ({data.get('name','')}) → 财务{fin_count}条 公告{ann_count}条")
            except Exception as e:
                db.rollback()
                log(f"  {stock_code} ERROR: {e}")
                import traceback; traceback.print_exc()

    log(f"导入完成！共财务{total_fin}条，公告{total_ann}条")


if __name__ == "__main__":
    main()
