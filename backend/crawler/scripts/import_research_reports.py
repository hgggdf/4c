"""医药行业研报临时导入脚本。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge.store import get_store
from app.paths import CRAWLER_STAGING_DIR, KNOWLEDGE_STORE_FILE
from crawler.scrapers.web_scraper import (
    fetch_eastmoney_industry_reports,
    fetch_eastmoney_stock_reports,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://data.eastmoney.com/",
}

STOCK_REPORT_APIS = [
    ("600276", "恒瑞医药"),
    ("603259", "药明康德"),
    ("300015", "爱尔眼科"),
]
DEFAULT_EXPORT_DIR = CRAWLER_STAGING_DIR / "research_reports"


def _build_report_api_params(*, code: str, limit: int) -> dict[str, str | int]:
    end_date = datetime.now().date()
    begin_date = end_date - timedelta(days=365)
    return {
        "cb": "datatable",
        "industryCode": "*",
        "pageSize": max(limit, 1),
        "pageNo": 1,
        "reportType": "R",
        "code": code,
        "p": 1,
        "pageNum": 1,
        "beginTime": begin_date.isoformat(),
        "endTime": end_date.isoformat(),
        "qType": 0,
    }


def fetch_industry_reports_api(keyword: str = "医药", limit: int = 5) -> list[dict]:
    """通过东方财富JSON接口抓行业研报列表"""
    try:
        resp = requests.get(
            "https://reportapi.eastmoney.com/report/list",
            headers=HEADERS,
            params=_build_report_api_params(code="*", limit=limit),
            timeout=15,
        )
        text = resp.text
        # 去掉 JSONP 包装
        if text.startswith("datatable("):
            text = text[10:-1]
        import json
        data = json.loads(text)
        items = data.get("data", [])
        results = []
        for item in items:
            title = item.get("title", "")
            if keyword not in title and keyword != "*":
                continue
            results.append({
                "title": title,
                "org": item.get("orgSName", ""),
                "date": item.get("publishDate", "")[:10],
                "stock": item.get("stockName", ""),
                "stock_code": item.get("stockCode", ""),
                "rating": item.get("starRating", ""),
                "abstract": item.get("summary", "") or item.get("infoCode", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_stock_reports_api(stock_code: str, limit: int = 3) -> list[dict]:
    """抓个股研报"""
    try:
        resp = requests.get(
            "https://reportapi.eastmoney.com/report/list",
            headers=HEADERS,
            params=_build_report_api_params(code=stock_code, limit=limit),
            timeout=15,
        )
        text = resp.text
        if text.startswith("datatable("):
            text = text[10:-1]
        import json
        data = json.loads(text)
        items = data.get("data", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "org": item.get("orgSName", ""),
                "date": item.get("publishDate", "")[:10],
                "stock": item.get("stockName", ""),
                "stock_code": item.get("stockCode", ""),
                "rating": item.get("starRating", ""),
                "abstract": item.get("summary", "") or item.get("infoCode", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def _valid_reports(items: list[dict]) -> list[dict]:
    return [item for item in items if "error" not in item and item.get("title")]


def _parse_stock_target(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split("|", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError("stock must use '股票代码|股票名称' format")
    return parts[0], parts[1]


def fetch_industry_reports(keyword: str = "医药", limit: int = 5) -> tuple[list[dict], list[str]]:
    api_reports = fetch_industry_reports_api(keyword=keyword, limit=limit)
    valid = _valid_reports(api_reports)
    notes: list[str] = []
    if valid:
        notes.append("industry:api")
        return valid, notes

    if api_reports and "error" in api_reports[0]:
        notes.append(f"industry_api_error={api_reports[0]['error']}")

    fallback_reports = fetch_eastmoney_industry_reports(keyword=keyword, limit=limit)
    fallback_valid = _valid_reports(fallback_reports)
    if fallback_valid:
        notes.append("industry:web_scraper")
        return fallback_valid, notes

    if fallback_reports and "error" in fallback_reports[0]:
        notes.append(f"industry_web_error={fallback_reports[0]['error']}")
    return [], notes


def fetch_stock_reports(stock_code: str, *, limit: int = 3) -> tuple[list[dict], list[str]]:
    api_reports = fetch_stock_reports_api(stock_code, limit=limit)
    valid = _valid_reports(api_reports)
    notes: list[str] = []
    if valid:
        notes.append("stock:api")
        return valid, notes

    if api_reports and "error" in api_reports[0]:
        notes.append(f"stock_api_error={api_reports[0]['error']}")

    fallback_reports = fetch_eastmoney_stock_reports(stock_code, limit=limit)
    fallback_valid = _valid_reports(fallback_reports)
    if fallback_valid:
        notes.append("stock:web_scraper")
        return fallback_valid, notes

    if fallback_reports and "error" in fallback_reports[0]:
        notes.append(f"stock_web_error={fallback_reports[0]['error']}")
    return [], notes


def build_report_text(report: dict, stock_name: str = "") -> str:
    """把研报元数据拼成可检索的文本段落"""
    parts = []
    if stock_name:
        parts.append(f"公司：{stock_name}")
    elif report.get("stock"):
        parts.append(f"公司：{report['stock']}")
    if report.get("title"):
        parts.append(f"标题：{report['title']}")
    if report.get("org"):
        parts.append(f"机构：{report['org']}")
    if report.get("date"):
        parts.append(f"日期：{report['date']}")
    if report.get("rating"):
        parts.append(f"评级：{report['rating']}")
    if report.get("summary"):
        parts.append(f"摘要：{report['summary']}")
    if report.get("source"):
        parts.append(f"来源：{report['source']}")
    # 从标题中提取关键信息作为摘要
    title = report.get("title", "")
    if any(kw in title for kw in ["增持", "买入", "推荐", "强烈推荐"]):
        parts.append("投资建议：看多")
    elif any(kw in title for kw in ["中性", "持有", "观望"]):
        parts.append("投资建议：中性")
    elif any(kw in title for kw in ["减持", "卖出"]):
        parts.append("投资建议：看空")
    return "\n".join(parts)


def _build_store_meta(report: dict, *, source_label: str, stock_code: str = "", stock_name: str = "") -> dict:
    return {
        "source": source_label,
        "type": "research_report",
        "title": report.get("title", ""),
        "date": report.get("date", ""),
        "org": report.get("org", ""),
        "rating": report.get("rating", ""),
        "stock_code": stock_code,
        "stock_name": stock_name or report.get("stock", ""),
    }


def _background_records() -> list[dict]:
    background_texts = [
        """医药生物行业核心分析框架：
研发投入占比是衡量创新药企业竞争力的核心指标，通常创新药企业研发费用率在10%-20%之间。
毛利率反映产品定价能力，创新药毛利率通常在80%以上，仿制药在50%-70%，CXO企业在35%-45%。
ROE（净资产收益率）衡量股东回报，医药行业优质企业ROE通常在15%以上。
资产负债率反映财务风险，医药企业资产负债率通常低于50%为健康水平。
集采政策是影响仿制药企业盈利的重要因素，中标企业以价换量，未中标企业面临市场萎缩风险。""",

        """恒瑞医药(600276)公司简介：
恒瑞医药是中国最大的创新药企业之一，主要产品涵盖抗肿瘤、手术麻醉、造影剂等领域。
研发管线丰富，在研项目超过100个，多个产品处于III期临床阶段。
近年来受集采政策影响，仿制药收入下滑，但创新药收入持续增长，2024年创新药收入占比超过50%。
主要风险：集采降价压力、研发失败风险、医保谈判降价风险。
主要机会：创新药出海（已有多个产品在美国、欧洲申报）、ADC药物管线布局领先。""",

        """药明康德(603259)公司简介：
药明康德是全球领先的CXO（合同研究与生产）平台型企业，提供从药物发现到商业化生产的全链条服务。
业务分为化学业务（WuXi Chemistry）、测试业务、生物学业务、细胞基因治疗（CTDMO）四大板块。
TIDES业务（多肽/寡核苷酸）是当前最大亮点，受GLP-1减肥药需求爆发带动，增速超60%。
主要风险：美国《生物安全法案》立法风险（美国客户收入占比约65%）、全球Biotech融资寒冬。
主要机会：TIDES产能全球领先、一体化CRDMO模式客户黏性强、估值已大幅回调至历史低位。""",

        """爱尔眼科(300015)公司简介：
爱尔眼科是中国最大的眼科医疗连锁机构，采用分级连锁模式在全国布局超过800家医院。
主要业务：屈光手术（近视矫正）、白内障手术、眼底病治疗、视光服务。
收入结构：屈光手术约占35%，白内障约占20%，视光服务约占15%，其余为综合眼病。
毛利率稳定在50%左右，净利率约17%，ROE约18%，财务质量较高。
主要风险：医疗事故风险、并购整合风险、消费降级对自费项目的影响。
主要机会：中国近视人口基数大、老龄化带动白内障需求、海外扩张（东南亚、欧洲）。""",

        """医药行业政策环境分析：
集采政策：国家组织药品集中采购已进行多轮，仿制药价格大幅下降，倒逼企业转型创新药。
医保谈判：每年医保目录调整，创新药通过谈判进入医保后以价换量，短期降价但长期放量。
DRG/DIP支付改革：按病种付费改革推进，医院控费压力增大，对高值耗材和辅助用药冲击较大。
创新药审评加速：优先审评、突破性疗法认定等政策加速创新药上市，利好创新药企业。
CXO监管：美国《生物安全法案》针对中国CXO企业，若立法落地将对药明康德等企业产生重大影响。""",

        """医药行业CXO赛道分析：
CXO（合同研究与生产外包）是医药产业链中增长最快的细分赛道之一。
CRO（合同研究组织）：提供临床前和临床研究服务，代表企业：药明康德、康龙化成、泰格医药。
CDMO（合同研发与生产组织）：提供工艺开发和商业化生产服务，代表企业：药明康德、凯莱英。
行业景气度：2021-2022年受Biotech融资热潮驱动高速增长，2023年起受融资寒冬影响增速放缓。
竞争格局：药明康德规模最大，具有平台优势；凯莱英在小分子CDMO领域专业化程度高。""",
    ]
    records: list[dict] = []
    for text in background_texts:
        title = text.split("\n", 1)[0].strip("：").strip()
        records.append(
            {
                "text": text,
                "meta": {"source": "医药行业知识库", "type": "background", "title": title},
                "origin": "background",
            }
        )
    return records


def _build_import_records(
    *,
    industry_keyword: str,
    industry_limit: int,
    stock_targets: list[tuple[str, str]],
    stock_limit: int,
    include_background: bool,
) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    notes: list[str] = []

    print(f"正在抓取医药行业研报，关键词={industry_keyword}...")
    industry_reports, industry_notes = fetch_industry_reports(keyword=industry_keyword, limit=industry_limit)
    notes.extend(industry_notes)
    for report in industry_reports:
        records.append(
            {
                "text": build_report_text(report),
                "meta": _build_store_meta(report, source_label="东方财富行业研报"),
                "origin": "industry_report",
            }
        )
    print(f"  [OK] 行业研报 {len(industry_reports)} 篇")

    for code, name in stock_targets:
        print(f"正在抓取 {name}({code}) 个股研报...")
        time.sleep(1)
        reports, stock_notes = fetch_stock_reports(code, limit=stock_limit)
        notes.extend([f"{code}:{note}" for note in stock_notes])
        for report in reports:
            records.append(
                {
                    "text": build_report_text(report, stock_name=name),
                    "meta": _build_store_meta(
                        report,
                        source_label=f"东方财富个股研报/{name}",
                        stock_code=code,
                        stock_name=name,
                    ),
                    "origin": "stock_report",
                }
            )
        print(f"  [OK] {name} 研报 {len(reports)} 篇")

    if include_background:
        print("写入医药行业背景知识...")
        background = _background_records()
        records.extend(background)
        print(f"  [OK] 背景知识 {len(background)} 条")

    return records, notes


def _export_records(records: list[dict], *, export_dir: Path) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = export_dir / f"research_reports_{timestamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "records": records,
    }
    export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path = export_dir / "research_reports_latest.json"
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return export_path


def import_reports_to_knowledge_store(
    *,
    industry_keyword: str = "医药",
    industry_limit: int = 10,
    stock_targets: list[tuple[str, str]] | None = None,
    stock_limit: int = 3,
    include_background: bool = True,
    export_dir: Path | None = None,
) -> dict:
    """抓取行业与个股研报，并写入 legacy knowledge store。"""
    store = get_store()
    before_docs = len(store.docs)
    targets = stock_targets or STOCK_REPORT_APIS
    records, notes = _build_import_records(
        industry_keyword=industry_keyword,
        industry_limit=industry_limit,
        stock_targets=targets,
        stock_limit=stock_limit,
        include_background=include_background,
    )

    for record in records:
        store.add_document(record["text"], metadata=record["meta"])

    export_path = _export_records(records, export_dir=export_dir or DEFAULT_EXPORT_DIR)
    summary = {
        "knowledge_store_path": str(KNOWLEDGE_STORE_FILE),
        "export_path": str(export_path),
        "industry_keyword": industry_keyword,
        "industry_limit": industry_limit,
        "stock_targets": [{"stock_code": code, "stock_name": name} for code, name in targets],
        "stock_limit": stock_limit,
        "include_background": include_background,
        "imported_records": len(records),
        "knowledge_store_docs_before": before_docs,
        "knowledge_store_docs_after": len(store.docs),
        "notes": notes,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Temporary Eastmoney research report importer for the legacy local knowledge store."
    )
    parser.add_argument("--industry-keyword", default="医药", help="Keyword used to filter industry reports")
    parser.add_argument("--industry-limit", type=int, default=10, help="Max number of industry reports to fetch")
    parser.add_argument(
        "--stock",
        action="append",
        dest="stocks",
        type=_parse_stock_target,
        help="Stock target in '股票代码|股票名称' format. Repeatable. Defaults to built-in pharma examples.",
    )
    parser.add_argument("--stock-limit", type=int, default=3, help="Max number of reports to fetch per stock")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Directory used to export the imported temporary research report batch",
    )
    parser.add_argument("--skip-background", action="store_true", help="Do not import the built-in pharma background texts")
    args = parser.parse_args()

    import_reports_to_knowledge_store(
        industry_keyword=args.industry_keyword,
        industry_limit=max(args.industry_limit, 0),
        stock_targets=args.stocks,
        stock_limit=max(args.stock_limit, 0),
        include_background=not args.skip_background,
        export_dir=args.export_dir,
    )


if __name__ == "__main__":
    main()
