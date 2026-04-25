#!/usr/bin/env python
"""
OpenClaw 集成演示脚本

演示如何使用 OpenClaw 统一入库接口导入各类数据。
包含完整的使用流程和最佳实践。
"""

import requests
import json
import time
from datetime import datetime


class OpenClawDemo:
    """OpenClaw 集成演示"""

    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.ingest_url = f"{base_url}/api/openclaw/ingest"

    def print_section(self, title):
        """打印章节标题"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_step(self, step, description):
        """打印步骤"""
        print(f"\n[步骤 {step}] {description}")
        print("-" * 70)

    def check_service(self):
        """检查服务状态"""
        self.print_step(1, "检查服务状态")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 服务状态: {data.get('status', 'unknown')}")
                print(f"✓ 数据库状态: {data.get('database', {}).get('available', False)}")
                return True
            else:
                print(f"✗ 服务健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 无法连接到服务: {e}")
            print("\n请确保后端服务已启动:")
            print("  cd C:\\Users\\17614\\Desktop\\4c\\backend")
            print("  python main.py")
            return False

    def demo_company_profile(self):
        """演示：导入公司概况"""
        self.print_step(2, "导入公司概况")

        data = {
            "batch_id": f"{datetime.now().strftime('%Y%m%d')}_demo_001",
            "task_id": "demo_company_profile",
            "source": {
                "source_type": "official_website",
                "source_name": "公司官网",
                "source_url": "https://www.hengrui.com",
                "source_category": "company"
            },
            "entity": {
                "entity_type": "company",
                "stock_code": "600276",
                "stock_name": "恒瑞医药",
                "industry_code": "IND_MED_01",
                "industry_name": "医药制造"
            },
            "document": {
                "doc_type": "html",
                "title": "恒瑞医药公司简介",
                "publish_time": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "file_hash": "sha256:demo_company",
                "raw_file_path": "/data/demo/company/600276/profile.html",
                "language": "zh"
            },
            "payload_type": "company_profile",
            "payload": {
                "business_summary": "江苏恒瑞医药股份有限公司是一家从事医药创新和高品质药品研发、生产及推广的医药健康企业，创建于1970年。公司致力于成为具有国际竞争力的创新型制药企业。",
                "core_products_json": [
                    "抗肿瘤药物",
                    "手术麻醉药物",
                    "造影剂",
                    "心血管药物"
                ],
                "main_segments_json": [
                    "创新药研发",
                    "仿制药生产",
                    "原料药销售",
                    "国际化业务"
                ],
                "market_position": "国内领先的创新药企业，研发投入占比持续保持在15%以上，多个创新药产品处于临床试验阶段或已上市。",
                "management_summary": "公司拥有经验丰富的管理团队和强大的研发团队，核心管理人员平均从业年限超过20年，研发人员占比超过30%。"
            },
            "processing": {
                "parse_status": "parsed",
                "parse_method": "html_extraction",
                "confidence_score": 0.95,
                "version_no": "v1"
            },
            "extra": {
                "demo": True,
                "note": "演示数据"
            }
        }

        print("\n发送请求...")
        print(f"URL: {self.ingest_url}")
        print(f"Payload Type: {data['payload_type']}")
        print(f"Stock Code: {data['entity']['stock_code']}")

        try:
            response = requests.post(self.ingest_url, json=data, timeout=30)
            print(f"\n响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✓ 导入成功!")
                print(f"\n响应数据:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return True
            else:
                print("✗ 导入失败!")
                print(f"错误: {response.text}")
                return False
        except Exception as e:
            print(f"✗ 请求失败: {e}")
            return False

    def demo_financial_statement(self):
        """演示：导入财务报表"""
        self.print_step(3, "导入财务报表（利润表）")

        data = {
            "batch_id": f"{datetime.now().strftime('%Y%m%d')}_demo_002",
            "task_id": "demo_financial_statement",
            "source": {
                "source_type": "annual_report",
                "source_name": "恒瑞医药2024年年度报告",
                "source_url": "https://example.com/report/600276_2024.pdf",
                "source_category": "financial_report"
            },
            "entity": {
                "entity_type": "company",
                "stock_code": "600276",
                "stock_name": "恒瑞医药"
            },
            "document": {
                "doc_type": "pdf",
                "title": "恒瑞医药2024年年度报告",
                "publish_time": "2025-04-19T00:00:00+08:00",
                "crawl_time": datetime.now().isoformat(),
                "file_hash": "sha256:demo_financial",
                "raw_file_path": "/data/demo/financial/600276/2024/annual_report.pdf",
                "language": "zh"
            },
            "payload_type": "financial_statement",
            "payload": {
                "statement_type": "income_statement",
                "report_date": "2024-12-31",
                "revenue": 28500000000,
                "operating_cost": 4700000000,
                "gross_profit": 23800000000,
                "selling_expense": 8500000000,
                "admin_expense": 1200000000,
                "rd_expense": 5800000000,
                "operating_profit": 7200000000,
                "net_profit": 6500000000,
                "net_profit_deducted": 6300000000,
                "eps": 3.45
            },
            "processing": {
                "parse_status": "parsed",
                "parse_method": "pdf_table_extraction",
                "confidence_score": 0.96,
                "version_no": "v1"
            },
            "extra": {
                "fiscal_year": 2024,
                "report_type": "annual",
                "demo": True
            }
        }

        print("\n发送请求...")
        print(f"Payload Type: {data['payload_type']}")
        print(f"Statement Type: {data['payload']['statement_type']}")
        print(f"Report Date: {data['payload']['report_date']}")
        print(f"Revenue: ¥{data['payload']['revenue']:,}")
        print(f"Net Profit: ¥{data['payload']['net_profit']:,}")

        try:
            response = requests.post(self.ingest_url, json=data, timeout=30)
            print(f"\n响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✓ 导入成功!")
                return True
            else:
                print("✗ 导入失败!")
                print(f"错误: {response.text}")
                return False
        except Exception as e:
            print(f"✗ 请求失败: {e}")
            return False

    def demo_announcement(self):
        """演示：导入公告"""
        self.print_step(4, "导入公告原始数据")

        data = {
            "batch_id": f"{datetime.now().strftime('%Y%m%d')}_demo_003",
            "task_id": "demo_announcement",
            "source": {
                "source_type": "official_website",
                "source_name": "上海证券交易所",
                "source_url": "http://www.sse.com.cn/disclosure/listedinfo/announcement/",
                "source_category": "announcement"
            },
            "entity": {
                "entity_type": "company",
                "stock_code": "600276",
                "stock_name": "恒瑞医药"
            },
            "document": {
                "doc_type": "html",
                "title": "恒瑞医药关于创新药获批临床试验的公告",
                "publish_time": datetime.now().isoformat(),
                "crawl_time": datetime.now().isoformat(),
                "file_hash": "sha256:demo_announcement",
                "raw_file_path": "/data/demo/announcement/600276/demo.html",
                "language": "zh"
            },
            "payload_type": "announcement_raw",
            "payload": {
                "announcement_type": "approval",
                "content": "本公司及董事会全体成员保证信息披露的内容真实、准确、完整。江苏恒瑞医药股份有限公司（以下简称"公司"）近日收到国家药品监督管理局核准签发的《药物临床试验批准通知书》，同意公司自主研发的创新药XX进行临床试验。该药物用于治疗XX疾病，目前处于临床前研究阶段。公司将按照相关法规要求，积极推进该药物的临床试验工作。",
                "exchange": "SSE"
            },
            "processing": {
                "parse_status": "raw",
                "parse_method": "html",
                "confidence_score": 1.0,
                "version_no": "v1"
            },
            "extra": {
                "demo": True
            }
        }

        print("\n发送请求...")
        print(f"Payload Type: {data['payload_type']}")
        print(f"Title: {data['document']['title']}")
        print(f"Announcement Type: {data['payload']['announcement_type']}")

        try:
            response = requests.post(self.ingest_url, json=data, timeout=30)
            print(f"\n响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✓ 导入成功!")
                return True
            else:
                print("✗ 导入失败!")
                print(f"错误: {response.text}")
                return False
        except Exception as e:
            print(f"✗ 请求失败: {e}")
            return False

    def verify_data(self):
        """验证导入的数据"""
        self.print_step(5, "验证导入的数据")

        print("\n查询公司信息...")
        try:
            response = requests.get(
                f"{self.base_url}/api/stock/company",
                params={"symbol": "600276"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print("✓ 公司信息查询成功")
                print(f"  公司名称: {data.get('stock_name', 'N/A')}")
                print(f"  股票代码: {data.get('stock_code', 'N/A')}")
            else:
                print(f"✗ 查询失败: {response.status_code}")
        except Exception as e:
            print(f"✗ 查询失败: {e}")

        print("\n查询财务诊断...")
        try:
            response = requests.get(
                f"{self.base_url}/api/analysis/diagnose",
                params={"symbol": "600276", "year": 2024},
                timeout=10
            )
            if response.status_code == 200:
                print("✓ 财务诊断查询成功")
            else:
                print(f"✗ 查询失败: {response.status_code}")
        except Exception as e:
            print(f"✗ 查询失败: {e}")

    def run_demo(self):
        """运行完整演示"""
        self.print_section("OpenClaw 统一入库接口演示")

        print("\n本演示将展示如何使用 OpenClaw 接口导入各类数据：")
        print("  1. 检查服务状态")
        print("  2. 导入公司概况")
        print("  3. 导入财务报表")
        print("  4. 导入公告数据")
        print("  5. 验证导入结果")

        input("\n按 Enter 键开始演示...")

        # 步骤1: 检查服务
        if not self.check_service():
            print("\n✗ 演示终止：服务不可用")
            return

        time.sleep(1)

        # 步骤2: 导入公司概况
        success1 = self.demo_company_profile()
        time.sleep(1)

        # 步骤3: 导入财务报表
        success2 = self.demo_financial_statement()
        time.sleep(1)

        # 步骤4: 导入公告
        success3 = self.demo_announcement()
        time.sleep(1)

        # 步骤5: 验证数据
        self.verify_data()

        # 总结
        self.print_section("演示总结")
        print(f"\n公司概况导入: {'✓ 成功' if success1 else '✗ 失败'}")
        print(f"财务报表导入: {'✓ 成功' if success2 else '✗ 失败'}")
        print(f"公告数据导入: {'✓ 成功' if success3 else '✗ 失败'}")

        success_count = sum([success1, success2, success3])
        print(f"\n总计: {success_count}/3 个演示成功")

        if success_count == 3:
            print("\n✓ 所有演示成功完成！")
            print("\n接下来您可以:")
            print("  1. 查看完整文档: OPENCLAW_README.md")
            print("  2. 运行自动化测试: python test_openclaw_integration.py")
            print("  3. 生成测试数据: python generate_openclaw_test_data.py")
            print("  4. 批量导入数据: python batch_import_openclaw.py data.json")
        else:
            print("\n部分演示失败，请检查:")
            print("  1. 后端服务是否正常运行")
            print("  2. 数据库连接是否正常")
            print("  3. 查看后端日志获取详细错误信息")

        self.print_section("演示结束")


def main():
    """主函数"""
    demo = OpenClawDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()
