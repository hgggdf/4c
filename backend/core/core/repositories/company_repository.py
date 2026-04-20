from __future__ import annotations

import json
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.database.models.company import (
    CompanyMaster,
    CompanyProfile,
    CompanyIndustryMap,
    IndustryMaster,
)


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_stock_code(self, stock_code: str) -> CompanyMaster | None:
        stmt = select(CompanyMaster).where(CompanyMaster.stock_code == stock_code)
        return self.db.execute(stmt).scalars().first()

    def get_profile(self, stock_code: str) -> CompanyProfile | None:
        stmt = select(CompanyProfile).where(CompanyProfile.stock_code == stock_code)
        return self.db.execute(stmt).scalars().first()

    def list_industries(self, stock_code: str) -> list[IndustryMaster]:
        stmt = (
            select(IndustryMaster)
            .join(
                CompanyIndustryMap,
                CompanyIndustryMap.industry_code == IndustryMaster.industry_code,
            )
            .where(CompanyIndustryMap.stock_code == stock_code)
        )
        return list(self.db.execute(stmt).scalars().all())

    def search_by_name_or_alias(self, keyword: str, limit: int = 10) -> list[CompanyMaster]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        stmt = (
            select(CompanyMaster)
            .where(
                or_(
                    CompanyMaster.stock_name.ilike(f"%{kw}%"),
                    CompanyMaster.full_name.ilike(f"%{kw}%"),
                )
            )
            .limit(limit)
        )
        rows = list(self.db.execute(stmt).scalars().all())

        stmt_all = select(CompanyMaster).limit(5000)
        all_rows = list(self.db.execute(stmt_all).scalars().all())

        alias_hits = []
        for row in all_rows:
            alias_raw = row.alias_json
            aliases = []

            if isinstance(alias_raw, list):
                aliases = alias_raw
            elif isinstance(alias_raw, str):
                try:
                    parsed = json.loads(alias_raw)
                    if isinstance(parsed, list):
                        aliases = parsed
                    else:
                        aliases = [alias_raw]
                except Exception:
                    aliases = [alias_raw]

            if any(kw in str(alias) for alias in aliases):
                alias_hits.append(row)

        seen = set()
        merged = []
        for row in rows + alias_hits:
            if row.stock_code not in seen:
                seen.add(row.stock_code)
                merged.append(row)

        return merged[:limit]

    def resolve_company_from_text(self, text: str, limit: int = 5) -> list[CompanyMaster]:
        text = (text or "").strip()
        if not text:
            return []

        stmt = select(CompanyMaster).limit(5000)
        all_rows = list(self.db.execute(stmt).scalars().all())

        direct_hits = []

        for row in all_rows:
            candidates = [row.stock_name or "", row.full_name or ""]

            alias_raw = row.alias_json
            if isinstance(alias_raw, list):
                candidates.extend([str(x) for x in alias_raw])
            elif isinstance(alias_raw, str):
                try:
                    parsed = json.loads(alias_raw)
                    if isinstance(parsed, list):
                        candidates.extend([str(x) for x in parsed])
                    else:
                        candidates.append(alias_raw)
                except Exception:
                    candidates.append(alias_raw)

            candidates = [c.strip() for c in candidates if c and str(c).strip()]
            if any(c in text for c in candidates):
                direct_hits.append(row)

        if direct_hits:
            direct_hits.sort(
                key=lambda r: len((r.full_name or r.stock_name or "")),
                reverse=True,
            )
            dedup = []
            seen = set()
            for row in direct_hits:
                if row.stock_code not in seen:
                    seen.add(row.stock_code)
                    dedup.append(row)
            return dedup[:limit]

        import re

        candidates = re.findall(r"[\u4e00-\u9fff]{2,10}", text)
        for cand in sorted(candidates, key=len, reverse=True):
            rows = self.search_by_name_or_alias(cand, limit=limit)
            if rows:
                return rows

        return []