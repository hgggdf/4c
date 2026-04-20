"""
医药行业研报采集脚本
从东方财富抓取医药行业研报，切块存入知识库
"""
from __future__ import annotations

import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from bs4 import BeautifulSoup
from app.data.knowledge_store import get_store

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://data.eastmoney.com/",
}

# 东方财富研报 API（JSON接口，比HTML更稳定）
INDUSTRY_REPORT_API = (
    "https://reportapi.eastmoney.com/report/list"
    "?cb=datatable&industryCode=*&pageSize=20&pageNo=1"
    "&reportType=R&code=*&p=1&pageNum=1&_=1713600000000"
)

STOCK_REPORT_APIS = [
    ("600276", "恒瑞医药"),
    ("603259", "药明康德"),
    ("300015", "爱尔眼科"),
]


def fetch_industry_reports_api(keyword: str = "医药", limit: int = 5) -> list[dict]:
    """通过东方财富JSON接口抓行业研报列表"""
    url = (
        "https://reportapi.eastmoney.com/report/list"
        f"?cb=datatable&industryCode=*&pageSize={limit}&pageNo=1"
        "&reportType=R&code=*&p=1&pageNum=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
                "rating": item.get("starRating", ""),
                "abstract": item.get("infoCode", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_stock_reports_api(stock_code: str, limit: int = 3) -> list[dict]:
    """抓个股研报"""
    url = (
        "https://reportapi.eastmoney.com/report/list"
        f"?cb=datatable&industryCode=*&pageSize={limit}&pageNo=1"
        f"&reportType=R&code={stock_code}&p=1&pageNum=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
                "rating": item.get("starRating", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def build_report_text(report: dict, stock_name: str = "") -> str:
    """把研报元数据拼成可检索的文本段落"""
    parts = []
    if stock_name:
        parts.append(f"公司：{stock_name}")
    if report.get("title"):
        parts.append(f"标题：{report['title']}")
    if report.get("org"):
        parts.append(f"机构：{report['org']}")
    if report.get("date"):
        parts.append(f"日期：{report['date']}")
    if report.get("rating"):
        parts.append(f"评级：{report['rating']}")
    # 从标题中提取关键信息作为摘要
    title = report.get("title", "")
    if any(kw in title for kw in ["增持", "买入", "推荐", "强烈推荐"]):
        parts.append("投资建议：看多")
    elif any(kw in title for kw in ["中性", "持有", "观望"]):
        parts.append("投资建议：中性")
    elif any(kw in title for kw in ["减持", "卖出"]):
        parts.append("投资建议：看空")
    return "\n".join(parts)


def import_reports_to_knowledge_store() -> None:
    """抓取行业与个股研报，并写入知识库供问答检索使用。"""
    store = get_store()
    total = 0

    # 1. 行业研报（医药方向）
    print("正在抓取医药行业研报...")
    industry_reports = fetch_industry_reports_api(keyword="医药", limit=10)
    valid = [r for r in industry_reports if "error" not in r and r.get("title")]

    if valid:
        for r in valid:
            text = build_report_text(r)
            store.add(text, meta={"source": "东方财富行业研报", "type": "research_report",
                                   "title": r["title"], "date": r.get("date", "")})
            total += 1
        print(f"  [OK] 行业研报 {len(valid)} 篇")
    else:
        print("  [WARN] 行业研报抓取为空，写入备用数据")

    # 2. 三家公司个股研报
    for code, name in STOCK_REPORT_APIS:
        print(f"正在抓取 {name}({code}) 个股研报...")
        time.sleep(1)
        reports = fetch_stock_reports_api(code, limit=3)
        valid = [r for r in reports if "error" not in r and r.get("title")]
        if valid:
            for r in valid:
                text = build_report_text(r, stock_name=name)
                store.add(text, meta={"source": f"东方财富个股研报/{name}",
                                       "type": "research_report",
                                       "stock_code": code, "stock_name": name,
                                       "title": r["title"], "date": r.get("date", "")})
                total += 1
            print(f"  [OK] {name} 研报 {len(valid)} 篇")
        else:
            print(f"  [WARN] {name} 研报抓取为空")

    # 3. 写入医药行业背景知识（兜底，保证知识库有内容）
    print("写入医药行业背景知识...")
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

    for i, text in enumerate(background_texts):
        title = text.split("\n")[0].strip("：").strip()
        store.add(text, meta={"source": "医药行业知识库", "type": "background",
                               "title": title})
        total += 1

    print(f"  [OK] 背景知识 {len(background_texts)} 条")
    print(f"\n知识库入库完成，共 {total} 条，知识库总文档数: {len(store.docs)}")


if __name__ == "__main__":
    import_reports_to_knowledge_store()
