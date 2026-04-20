"""
将现有 TF-IDF 知识库内容 + 财务数据迁移到 ChromaDB 向量库
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy.orm import Session
from db.session import engine
from app.data.knowledge_store import get_store, get_vector_store
from db.repository.financial_repo import FinancialDataRepository
from db.repository.macro_repo import MacroIndicatorRepository


def migrate_tfidf_to_vector() -> None:
    """把 TF-IDF 知识库里的文档迁移到向量库"""
    tfidf = get_store()
    vs = get_vector_store()

    if not tfidf.docs:
        print("TF-IDF 知识库为空，跳过迁移")
        return

    print(f"正在迁移 {len(tfidf.docs)} 条文档到向量库...")
    for doc in tfidf.docs:
        vs.add(doc["text"], meta=doc["meta"])
    print(f"  [OK] 迁移完成，向量库当前: {vs.count()} 条")


def import_financial_to_vector() -> None:
    """把 financial_data 表的结构化数据转成文本存入向量库"""
    vs = get_vector_store()
    repo = FinancialDataRepository()

    companies = [
        ("600276", "恒瑞医药"),
        ("603259", "药明康德"),
        ("300015", "爱尔眼科"),
    ]

    print("正在将财务数据写入向量库...")
    total = 0

    with Session(engine) as db:
        for code, name in companies:
            for year in [2022, 2023, 2024]:
                rows = repo.get_by_company_year(db, code, year)
                if not rows:
                    continue

                # 把一家公司一年的所有指标拼成一段文本
                lines = [f"{name}（{code}）{year}年财务指标："]
                for r in rows:
                    val = f"{r.metric_value}{r.metric_unit or ''}" if r.metric_value is not None else "暂无"
                    lines.append(f"  {r.metric_name}: {val}")

                text = "\n".join(lines)
                n = vs.add(text, meta={
                    "source": f"{name}年报/{year}",
                    "type": "financial_data",
                    "stock_code": code,
                    "stock_name": name,
                    "year": str(year),
                })
                total += n

    print(f"  [OK] 财务数据写入 {total} 块，向量库当前: {vs.count()} 条")


def import_macro_to_vector() -> None:
    """把宏观数据写入向量库"""
    vs = get_vector_store()
    macro_repo = MacroIndicatorRepository()

    print("正在将宏观数据写入向量库...")

    with Session(engine) as db:
        lines = ["宏观经济指标数据："]
        for indicator in ["CPI同比增长率", "医疗保健CPI同比增长率", "GDP同比增长率"]:
            series = macro_repo.get_series(db, indicator)
            # 只取近3年年度数据
            annual = [r for r in series if len(r.period) == 4 and r.period >= "2022"]
            if annual:
                vals = "、".join(f"{r.period}年{r.value}{r.unit}" for r in annual)
                lines.append(f"  {indicator}：{vals}")

        text = "\n".join(lines)
        n = vs.add(text, meta={"source": "国家统计局宏观数据", "type": "macro"})

    print(f"  [OK] 宏观数据写入 {n} 块，向量库当前: {vs.count()} 条")


if __name__ == "__main__":
    migrate_tfidf_to_vector()
    import_financial_to_vector()
    import_macro_to_vector()
    print("\n全部完成！")
