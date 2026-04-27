"""股票与公司资料接口的数据库直连适配层。"""

from __future__ import annotations

from collections.abc import Iterable
import json

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementRawHot
from app.core.database.models.company import Company, CompanyMaster, IndustryMaster
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.news_hot import NewsHot, NewsRawHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.user import Watchlist

from .shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, normalize_percent, resolve_company, serialize_kline_row, to_float


class StockService:
    """为旧版 /api/stock/* URL 提供与当前数据库结构对齐的实现。"""

    def get_quote(self, db: Session, symbol: str) -> dict:
        company = self._require_company(db, symbol)
        latest = get_latest_trade_rows(db, [company.stock_code]).get(company.stock_code)
        return build_quote_payload(company, latest)

    def get_kline(self, db: Session, symbol: str, days: int = 30) -> list[dict]:
        company = self._require_company(db, symbol)
        rows = list(
            db.execute(
                select(FinancialHot)
                .where(FinancialHot.stock_code == company.stock_code)
                .order_by(FinancialHot.report_date.desc(), FinancialHot.created_at.desc())
                .limit(days)
            ).scalars().all()
        )
        rows.reverse()
        return [item for item in (serialize_kline_row(row) for row in rows) if item is not None]

    def get_watchlist(self, db: Session, user_id: int) -> list[dict]:
        user = ensure_demo_user(db, user_id)
        rows = self._list_watchlist_rows(db, user.id)
        if not rows:
            self._seed_default_watchlist(db, user.id)
            rows = self._list_watchlist_rows(db, user.id)
        return [
            {"symbol": company.stock_code, "name": company.stock_name}
            for _, company in rows
        ]

    def add_watchlist(self, db: Session, user_id: int, symbol: str, name: str | None):
        user = ensure_demo_user(db, user_id)
        company = self._require_company(db, symbol or name or "")

        existing = db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user.id,
                Watchlist.stock_code == company.stock_code,
            )
        ).scalars().first()
        if existing is None:
            db.add(
                Watchlist(
                    user_id=user.id,
                    stock_code=company.stock_code,
                    remark=None,
                    tags_json=None,
                    alert_enabled=1,
                )
            )
            db.commit()
        return {"symbol": company.stock_code, "name": company.stock_name}

    def remove_watchlist(self, db: Session, user_id: int, symbol: str):
        user = ensure_demo_user(db, user_id)
        company = resolve_company(db, symbol)
        if company is None:
            return {"removed": False}

        result = db.execute(
            delete(Watchlist).where(
                Watchlist.user_id == user.id,
                Watchlist.stock_code == company.stock_code,
            )
        )
        db.commit()
        return {"removed": bool(result.rowcount)}

    def list_pharma_companies(self, db: Session):
        companies = self._list_companies(db)
        latest_map = get_latest_trade_rows(db, [item.stock_code for item in companies])
        results = []
        for company in companies:
            quote = build_quote_payload(company, latest_map.get(company.stock_code))
            results.append(
                {
                    "symbol": company.stock_code,
                    "name": company.stock_name,
                    "exchange": company.exchange,
                    "industry_code": company.industry_code,
                    "industry_level1": company.industry_level1,
                    "industry_level2": company.industry_level2,
                    "status": getattr(company, "status", "active"),
                    "business_summary": company.business_summary,
                    "core_products_json": company.core_products_json,
                    "main_segments_json": company.main_segments_json,
                    "quote": quote,
                    "collected_at": quote["time"],
                }
            )
        return results

    def get_company_dataset(self, db: Session, symbol: str, refresh: bool = False, compact: bool = True):
        company = self._require_company(db, symbol)
        latest_map = get_latest_trade_rows(db, [company.stock_code])
        quote = build_quote_payload(company, latest_map.get(company.stock_code))
        dataset = {
            "symbol": company.stock_code,
            "name": company.stock_name,
            "exchange": company.exchange,
            "industry_code": company.industry_code,
            "industry_level1": company.industry_level1,
            "industry_level2": company.industry_level2,
            "company_status": getattr(company, "status", "active"),
            "business_summary": company.business_summary,
            "core_products_json": company.core_products_json,
            "main_segments_json": company.main_segments_json,
            "collected_at": quote["time"],
            "quote": quote,
            "kline": self.get_kline(db, company.stock_code, days=120),
            "company_info": self._build_company_info(company),
            "profile": self._build_profile_payload(db, company.stock_code),
            "industries": self._build_industries_payload(db, company.stock_code),
            "financial_abstract": self._build_financial_abstract(db, company.stock_code),
            "main_business": self._build_main_business(db, company.stock_code),
            "research_reports": self._build_research_reports(db, company.stock_code, compact=compact),
            "announcements": self._build_announcements(db, company.stock_code, compact=compact),
            "news": self._build_news(db, company.stock_code, compact=compact),
        }

        if compact:
            dataset["kline"] = dataset["kline"][-60:]
            dataset["announcements"] = dataset["announcements"][:8]
            dataset["news"] = dataset["news"][:8]
            dataset["main_business"] = dataset["main_business"][:8]
            dataset["research_reports"] = dataset["research_reports"][:12]

        return dataset

    def refresh_all_company_data(self, db: Session, compact: bool = True):
        companies = self.list_pharma_companies(db)
        return {
            "total": len(companies),
            "message": "当前接口已切换为数据库直读模式，不再触发外部抓取。",
            "companies": companies if compact else [item["symbol"] for item in companies],
        }

    def build_company_agent_context(self, db: Session, symbol: str) -> str:
        dataset = self.get_company_dataset(db, symbol, compact=True)
        parts = [
            f"公司：{dataset['name']}（{dataset['symbol']}）",
            f"交易所：{dataset.get('exchange') or '未知'}",
            f"最新价：{dataset['quote']['price']}",
        ]

        metrics = []
        for row in dataset.get("financial_abstract", [])[:5]:
            latest_entry = next(
                (
                    (key, value)
                    for key, value in row.items()
                    if key not in {"选项", "指标"} and value not in (None, "")
                ),
                None,
            )
            if latest_entry is not None:
                metrics.append(f"{row['指标']}（{latest_entry[0]}）：{latest_entry[1]}")
        if metrics:
            parts.append("财务摘要：" + "；".join(metrics))

        if dataset.get("announcements"):
            first = dataset["announcements"][0]
            parts.append(f"最新公告：{first['公告标题']}（{first['公告日期']}）")
        if dataset.get("news"):
            first = dataset["news"][0]
            parts.append(f"最新新闻：{first['新闻标题']}（{first['发布时间']}）")
        return "\n".join(parts)

    def get_db_stats(self, db: Session):
        return {
            "companies": db.execute(select(func.count()).select_from(CompanyMaster)).scalar_one(),
            "watchlists": db.execute(select(func.count()).select_from(Watchlist)).scalar_one(),
            "stock_daily": db.execute(select(func.count()).select_from(FinancialHot)).scalar_one(),
            "announcements": db.execute(select(func.count()).select_from(AnnouncementRawHot)).scalar_one(),
            "news": db.execute(select(func.count()).select_from(NewsRawHot)).scalar_one(),
        }

    def _require_company(self, db: Session, symbol: str) -> CompanyMaster:
        company = resolve_company(db, symbol)
        if company is None:
            raise ValueError(f"company not found: {symbol}")
        return company

    def _list_companies(self, db: Session) -> list[CompanyMaster]:
        return list(
            db.execute(
                select(CompanyMaster)
                .order_by(CompanyMaster.stock_code.asc())
            ).scalars().all()
        )

    def _list_watchlist_rows(self, db: Session, user_id: int):
        return list(
            db.execute(
                select(Watchlist, CompanyMaster)
                .join(CompanyMaster, CompanyMaster.stock_code == Watchlist.stock_code)
                .where(Watchlist.user_id == user_id)
                .order_by(Watchlist.created_at.desc(), Watchlist.id.desc())
            ).all()
        )

    def _seed_default_watchlist(self, db: Session, user_id: int) -> None:
        companies = list(
            db.execute(
                select(CompanyMaster)
                .order_by(CompanyMaster.stock_code.asc())
                .limit(3)
            ).scalars().all()
        )
        for company in companies:
            db.add(
                Watchlist(
                    user_id=user_id,
                    stock_code=company.stock_code,
                    remark="默认观察池",
                    tags_json=["default"],
                    alert_enabled=1,
                )
            )
        if companies:
            db.commit()

    def _build_company_info(self, company: CompanyMaster) -> dict:
        return {
            "股票简称": company.stock_name,
            "股票代码": company.stock_code,
            "公司全称": company.full_name or company.stock_name,
            "交易所": company.exchange or "",
            "行业代码": company.industry_code or "",
            "一级行业": company.industry_level1 or "",
            "二级行业": company.industry_level2 or "",
            "上市时间": company.listing_date.isoformat() if company.listing_date else "",
            "公司状态": getattr(company, "status", "active"),
        }

    def _build_profile_payload(self, db: Session, stock_code: str) -> dict | None:
        company = db.execute(
            select(CompanyMaster).where(CompanyMaster.stock_code == stock_code)
        ).scalars().first()
        if company is None:
            return None
        return {
            "business_summary": company.business_summary,
            "core_products_json": company.core_products_json,
            "main_segments_json": company.main_segments_json,
            "market_position": company.market_position,
            "management_summary": company.management_summary,
        }

    def _build_industries_payload(self, db: Session, stock_code: str) -> list[dict]:
        company = db.execute(
            select(CompanyMaster).where(CompanyMaster.stock_code == stock_code)
        ).scalars().first()
        if company is None:
            return []
        results = []
        if company.industry_code:
            industry = db.execute(
                select(IndustryMaster).where(IndustryMaster.industry_code == company.industry_code)
            ).scalars().first()
            if industry:
                results.append({
                    "industry_code": industry.industry_code,
                    "industry_name": industry.industry_name,
                    "industry_level": getattr(industry, "industry_level", None),
                    "is_primary": True,
                    "description": industry.description,
                })
        if not results and (company.industry_level1 or company.industry_level2):
            results.append({
                "industry_code": company.industry_code or "",
                "industry_name": company.industry_level2 or company.industry_level1 or "",
                "industry_level": None,
                "is_primary": True,
                "description": None,
            })
        return results

    def _build_financial_abstract(self, db: Session, stock_code: str) -> list[dict]:
        all_rows = list(
            db.execute(
                select(FinancialHot)
                .where(FinancialHot.stock_code == stock_code)
                .order_by(FinancialHot.report_date.desc(), FinancialHot.created_at.desc())
                .limit(50)
            ).scalars().all()
        )

        by_year = self._latest_rows_by_year(all_rows, "fiscal_year")

        years = sorted(by_year.keys(), reverse=True)[:4]

        def row_payload(label: str, resolver):
            payload = {"选项": "核心指标", "指标": label}
            has_value = False
            for year in years:
                value = resolver(year)
                if value is None:
                    continue
                payload[str(year)] = round(value, 4)
                has_value = True
            return payload if has_value else None

        rows = [
            row_payload(
                "营业总收入",
                lambda year: to_float(getattr(by_year.get(year), "revenue", None), None),
            ),
            row_payload(
                "归母净利润",
                lambda year: to_float(getattr(by_year.get(year), "net_profit", None), None),
            ),
            row_payload(
                "扣非净利润",
                lambda year: to_float(getattr(by_year.get(year), "net_profit_deducted", None), None),
            ),
            row_payload(
                "净资产收益率(ROE)",
                lambda year: self._safe_ratio(
                    getattr(by_year.get(year), "net_profit", None),
                    getattr(by_year.get(year), "total_assets", None),
                ),
            ),
            row_payload(
                "毛利率",
                lambda year: normalize_percent(to_float(getattr(by_year.get(year), "gross_margin", None), None))
                or self._safe_ratio(
                    getattr(by_year.get(year), "gross_profit", None),
                    getattr(by_year.get(year), "revenue", None),
                ),
            ),
            row_payload(
                "资产负债率",
                lambda year: normalize_percent(to_float(getattr(by_year.get(year), "debt_ratio", None), None))
                or self._safe_ratio(
                    getattr(by_year.get(year), "total_liabilities", None),
                    getattr(by_year.get(year), "total_assets", None),
                ),
            ),
            row_payload(
                "经营现金流量净额",
                lambda year: to_float(getattr(by_year.get(year), "operating_cashflow", None), None),
            ),
            row_payload(
                "基本每股收益",
                lambda year: to_float(getattr(by_year.get(year), "eps", None), None),
            ),
        ]
        return [item for item in rows if item is not None]

    def _build_main_business(self, db: Session, stock_code: str) -> list[dict]:
        profile = db.execute(
            select(CompanyMaster).where(CompanyMaster.stock_code == stock_code)
        ).scalars().first()
        if profile is not None and profile.main_segments_json:
            raw = profile.main_segments_json
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raw = [raw]

            if isinstance(raw, list):
                items = []
                for item in raw:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("segment") or item.get("主营构成")
                    else:
                        name = str(item)
                    if name:
                        items.append({"分类类型": "按业务分类", "主营构成": name})
                if items:
                    return items

        industries = self._build_industries_payload(db, stock_code)
        return [
            {
                "分类类型": "按行业分类",
                "主营构成": item["industry_name"],
            }
            for item in industries
        ]

    def _build_announcements(self, db: Session, stock_code: str, compact: bool) -> list[dict]:
        limit = 8 if compact else 20
        rows = list(
            db.execute(
                select(AnnouncementRawHot)
                .where(AnnouncementRawHot.stock_code == stock_code)
                .order_by(AnnouncementRawHot.publish_date.desc(), AnnouncementRawHot.created_at.desc())
                .limit(limit)
            ).scalars().all()
        )
        return [
            {
                "公告日期": row.publish_date.isoformat() if row.publish_date else "",
                "公告标题": row.title,
                "公告类型": row.announcement_type,
                "来源链接": row.source_url,
            }
            for row in rows
        ]

    def _build_news(self, db: Session, stock_code: str, compact: bool) -> list[dict]:
        limit = 8 if compact else 20
        rows = list(
            db.execute(
                select(NewsHot)
                .where(NewsHot.related_stock_codes_json.isnot(None))
                .order_by(NewsHot.publish_time.desc(), NewsHot.created_at.desc())
                .limit(limit * 5)
            ).scalars().all()
        )
        matched = []
        for row in rows:
            codes = row.related_stock_codes_json
            if isinstance(codes, str):
                try:
                    codes = json.loads(codes)
                except Exception:
                    codes = [codes]
            if isinstance(codes, list) and stock_code in codes:
                matched.append(row)
            elif isinstance(codes, dict) and stock_code in codes:
                matched.append(row)
            if len(matched) >= limit:
                break
        return [
            {
                "发布时间": row.publish_time.isoformat() if row.publish_time else "",
                "新闻标题": row.title,
                "文章来源": row.source_name,
                "影响方向": "",
                "影响说明": row.summary_text or "",
                "新闻链接": row.source_url or "",
                "新闻内容": row.content or "",
            }
            for row in matched
        ]

    def _build_research_reports(self, db: Session, stock_code: str, compact: bool) -> list[dict]:
        limit = 12 if compact else 30
        rows = list(
            db.execute(
                select(ResearchReportHot)
                .where(ResearchReportHot.stock_code == stock_code)
                .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
                .limit(limit)
            ).scalars().all()
        )
        return [
            {
                "序号": i + 1,
                "报告名称": row.title,
                "机构": row.report_org or "--",
                "行业": "",
                "日期": row.publish_date.isoformat() if row.publish_date else "--",
                "东财评级": "",
                "报告PDF链接": row.source_url or "",
            }
            for i, row in enumerate(rows)
        ]

    def _latest_rows_by_year(self, rows: Iterable, year_attr: str) -> dict[int, object]:
        grouped: dict[int, object] = {}
        for row in rows:
            year = getattr(row, year_attr, None)
            if year is None:
                report_date = getattr(row, "report_date", None)
                year = report_date.year if report_date is not None else None
            if year is None or year in grouped:
                continue
            grouped[int(year)] = row
        return grouped

    def _safe_ratio(self, numerator, denominator) -> float | None:
        num = to_float(numerator, None)
        den = to_float(denominator, None)
        if num is None or den in (None, 0):
            return None
        return round(num / den * 100, 4)