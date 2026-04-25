#!/usr/bin/env python
"""
OpenClaw 数据生成器

用于生成符合 OpenClaw 统一格式的测试数据。
可以快速生成各种类型的测试数据用于接口测试。
"""

from datetime import datetime, timedelta
import random
import json


class OpenClawDataGenerator:
    """OpenClaw 测试数据生成器"""

    def __init__(self, stock_code="600276", stock_name="恒瑞医药"):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.batch_counter = 1

    def _get_batch_id(self):
        """生成批次号"""
        today = datetime.now().strftime("%Y%m%d")
        batch_id = f"{today}_{self.batch_counter:04d}"
        self.batch_counter += 1
        return batch_id

    def _base_envelope(self, task_id, source_category, entity_type="company"):
        """生成基础 envelope"""
        now = datetime.now()
        return {
            "batch_id": self._get_batch_id(),
            "task_id": task_id,
            "source": {
                "source_type": "test_generator",
                "source_name": "测试数据生成器",
                "source_url": f"https://test.example.com/{task_id}",
                "source_category": source_category
            },
            "entity": {
                "entity_type": entity_type,
                "stock_code": self.stock_code if entity_type == "company" else None,
                "stock_name": self.stock_name if entity_type == "company" else None,
            },
            "document": {
                "doc_type": "json",
                "title": f"测试数据-{task_id}",
                "publish_time": now.isoformat(),
                "crawl_time": now.isoformat(),
                "file_hash": f"sha256:test_{task_id}",
                "raw_file_path": f"/data/test/{task_id}.json",
                "language": "zh"
            },
            "processing": {
                "parse_status": "parsed",
                "parse_method": "test_generator",
                "confidence_score": 1.0,
                "version_no": "v1"
            },
            "extra": {}
        }

    def generate_company_profile(self):
        """生成公司概况数据"""
        envelope = self._base_envelope("test_company_profile", "company")
        envelope["entity"]["industry_code"] = "IND_MED_01"
        envelope["entity"]["industry_name"] = "医药制造"
        envelope["payload_type"] = "company_profile"
        envelope["payload"] = {
            "business_summary": f"{self.stock_name}是一家专注于创新药研发和生产的医药企业，主营业务包括抗肿瘤药、麻醉药、造影剂等领域。",
            "core_products_json": ["抗肿瘤药", "麻醉药", "造影剂", "心血管药"],
            "main_segments_json": ["创新药研发", "仿制药生产", "原料药销售"],
            "market_position": "国内领先的创新药企业，研发实力雄厚，多个产品处于行业领先地位。",
            "management_summary": "管理团队经验丰富，核心成员平均从业年限超过20年，研发投入占比持续保持在15%以上。"
        }
        return envelope

    def generate_financial_statement(self, year=2024, statement_type="income_statement"):
        """生成财务报表数据"""
        envelope = self._base_envelope(f"test_financial_{statement_type}_{year}", "financial_report")
        envelope["payload_type"] = "financial_statement"
        envelope["extra"] = {
            "fiscal_year": year,
            "report_type": "annual"
        }

        if statement_type == "income_statement":
            revenue = random.randint(20000000000, 30000000000)
            gross_profit = int(revenue * random.uniform(0.75, 0.85))
            net_profit = int(revenue * random.uniform(0.20, 0.25))
            envelope["payload"] = {
                "statement_type": "income_statement",
                "report_date": f"{year}-12-31",
                "revenue": revenue,
                "operating_cost": revenue - gross_profit,
                "gross_profit": gross_profit,
                "selling_expense": int(revenue * 0.30),
                "admin_expense": int(revenue * 0.04),
                "rd_expense": int(revenue * 0.20),
                "operating_profit": int(net_profit * 1.1),
                "net_profit": net_profit,
                "net_profit_deducted": int(net_profit * 0.97),
                "eps": round(net_profit / 1900000000, 2)
            }
        elif statement_type == "balance_sheet":
            total_assets = random.randint(40000000000, 60000000000)
            envelope["payload"] = {
                "statement_type": "balance_sheet",
                "report_date": f"{year}-12-31",
                "total_assets": total_assets,
                "total_liabilities": int(total_assets * 0.35),
                "accounts_receivable": int(total_assets * 0.10),
                "inventory": int(total_assets * 0.08),
                "cash": int(total_assets * 0.15),
                "equity": int(total_assets * 0.65),
                "goodwill": int(total_assets * 0.02)
            }
        elif statement_type == "cashflow_statement":
            operating_cf = random.randint(5000000000, 8000000000)
            envelope["payload"] = {
                "statement_type": "cashflow_statement",
                "report_date": f"{year}-12-31",
                "operating_cashflow": operating_cf,
                "investing_cashflow": -int(operating_cf * 0.3),
                "financing_cashflow": -int(operating_cf * 0.2),
                "free_cashflow": int(operating_cf * 0.7)
            }

        return envelope

    def generate_announcement_raw(self, announcement_type="approval"):
        """生成公告原始数据"""
        envelope = self._base_envelope(f"test_announcement_{announcement_type}", "announcement")
        envelope["document"]["doc_type"] = "html"
        envelope["document"]["title"] = f"{self.stock_name}关于新药获批的公告"
        envelope["payload_type"] = "announcement_raw"
        envelope["payload"] = {
            "announcement_type": announcement_type,
            "content": f"本公司及董事会全体成员保证信息披露的内容真实、准确、完整。{self.stock_name}近日收到国家药品监督管理局核准签发的关于XX药品的《药品注册证书》，该药品用于治疗XX疾病，预计将为公司带来新的增长点。",
            "exchange": "SSE"
        }
        return envelope

    def generate_drug_event(self, event_kind="drug_approval"):
        """生成药品事件数据"""
        envelope = self._base_envelope(f"test_drug_{event_kind}", "event")
        envelope["payload_type"] = "drug_event"

        drug_names = ["卡瑞利珠单抗", "阿帕替尼", "硫培非格司亭", "瑞马唑仑"]
        indications = ["非小细胞肺癌", "胃癌", "中性粒细胞减少症", "全身麻醉"]

        envelope["payload"] = {
            "event_kind": event_kind,
            "drug_name": random.choice(drug_names),
            "approval_type": "新药批准",
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
            "indication": random.choice(indications),
            "drug_stage": "approved",
            "is_innovative_drug": 1,
            "review_status": "approved",
            "market_scope": "national"
        }
        return envelope

    def generate_news_raw(self, news_type="policy"):
        """生成新闻原始数据"""
        envelope = self._base_envelope(f"test_news_{news_type}", "news")
        envelope["entity"]["entity_type"] = "article"
        envelope["document"]["title"] = "医药行业迎来政策利好"
        envelope["payload_type"] = "news_raw"

        news_uid = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        envelope["payload"] = {
            "news_uid": news_uid,
            "content": "据悉，国家医保局近日发布新政策，将进一步支持创新药纳入医保目录，这对医药行业尤其是创新药企业构成重大利好。业内人士认为，此举将加速创新药的市场推广，提升企业研发积极性。",
            "author_name": "测试记者",
            "news_type": news_type
        }
        return envelope

    def generate_macro_indicator(self, indicator_name="居民消费价格指数"):
        """生成宏观指标数据"""
        envelope = self._base_envelope(f"test_macro_{indicator_name}", "macro")
        envelope["entity"]["entity_type"] = "macro"
        envelope["payload_type"] = "macro_indicator"

        period = datetime.now().strftime("%Y-%m")
        envelope["payload"] = {
            "indicator_name": indicator_name,
            "period": period,
            "value": round(100 + random.uniform(0, 3), 2),
            "unit": "同比%"
        }
        return envelope

    def generate_stock_daily(self, trade_date=None):
        """生成股票日行情数据"""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        envelope = self._base_envelope(f"test_stock_daily_{trade_date}", "stock_daily")
        envelope["payload_type"] = "stock_daily"

        base_price = random.uniform(40, 50)
        envelope["payload"] = {
            "trade_date": trade_date,
            "open_price": round(base_price, 2),
            "close_price": round(base_price * random.uniform(0.98, 1.02), 2),
            "high_price": round(base_price * random.uniform(1.01, 1.05), 2),
            "low_price": round(base_price * random.uniform(0.95, 0.99), 2),
            "volume": random.randint(10000000, 20000000),
            "turnover": round(base_price * random.randint(400000000, 800000000), 2)
        }
        return envelope

    def generate_procurement_event(self):
        """生成集采事件数据"""
        envelope = self._base_envelope("test_procurement", "event")
        envelope["payload_type"] = "procurement_event"

        envelope["payload"] = {
            "event_kind": "centralized_procurement",
            "drug_name": "XX注射液",
            "procurement_round": "第十批",
            "bid_result": random.choice(["中标", "未中标"]),
            "price_change_ratio": round(random.uniform(-0.5, -0.2), 2),
            "event_date": datetime.now().strftime("%Y-%m-%d"),
            "impact_summary": "中标可能带来销量增长但价格下降影响毛利率"
        }
        return envelope

    def generate_trial_event(self):
        """生成临床试验事件数据"""
        envelope = self._base_envelope("test_trial", "event")
        envelope["payload_type"] = "trial_event"

        envelope["payload"] = {
            "event_kind": "clinical_trial",
            "drug_name": "创新药XX",
            "trial_phase": random.choice(["I期", "II期", "III期"]),
            "event_type": "phase_success",
            "event_date": datetime.now().strftime("%Y-%m-%d"),
            "indication": "肿瘤治疗",
            "summary_text": "临床试验达到主要终点，预计将申请上市"
        }
        return envelope

    def generate_regulatory_risk_event(self):
        """生成监管风险事件数据"""
        envelope = self._base_envelope("test_regulatory_risk", "event")
        envelope["payload_type"] = "regulatory_risk_event"

        envelope["payload"] = {
            "risk_type": random.choice(["regulatory_inquiry", "warning_letter", "inspection"]),
            "risk_level": random.choice(["low", "medium", "high"]),
            "event_date": datetime.now().strftime("%Y-%m-%d"),
            "summary_text": "公司收到监管问询函，需关注后续事项进展"
        }
        return envelope

    def generate_batch_data(self, count=5):
        """生成一批测试数据"""
        data_list = []

        # 公司概况
        data_list.append(self.generate_company_profile())

        # 财务报表
        for year in [2023, 2024]:
            data_list.append(self.generate_financial_statement(year, "income_statement"))
            data_list.append(self.generate_financial_statement(year, "balance_sheet"))
            data_list.append(self.generate_financial_statement(year, "cashflow_statement"))

        # 公告
        for _ in range(count):
            data_list.append(self.generate_announcement_raw())

        # 药品事件
        for _ in range(count):
            data_list.append(self.generate_drug_event())

        # 新闻
        for _ in range(count):
            data_list.append(self.generate_news_raw())

        # 宏观指标
        data_list.append(self.generate_macro_indicator())

        # 股票行情（最近5天）
        for i in range(5):
            trade_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            data_list.append(self.generate_stock_daily(trade_date))

        # 其他事件
        data_list.append(self.generate_procurement_event())
        data_list.append(self.generate_trial_event())
        data_list.append(self.generate_regulatory_risk_event())

        return data_list


def save_to_file(data_list, filename="openclaw_test_data.json"):
    """保存数据到文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    print(f"已生成 {len(data_list)} 条测试数据，保存到 {filename}")


def main():
    """主函数"""
    print("OpenClaw 测试数据生成器")
    print("=" * 60)

    generator = OpenClawDataGenerator(stock_code="600276", stock_name="恒瑞医药")

    # 生成批量数据
    data_list = generator.generate_batch_data(count=3)

    # 保存到文件
    save_to_file(data_list, "openclaw_test_data.json")

    # 打印示例
    print("\n示例数据（公司概况）：")
    print(json.dumps(data_list[0], ensure_ascii=False, indent=2))

    print("\n示例数据（财务报表）：")
    print(json.dumps(data_list[1], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
