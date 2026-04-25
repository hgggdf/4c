#!/usr/bin/env python
"""
OpenClaw 批量导入工具

用于批量导入 OpenClaw 格式的数据到 4C 系统。
支持从 JSON 文件读取数据并批量提交到入库接口。
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict
import argparse


class OpenClawBatchImporter:
    """OpenClaw 批量导入器"""

    def __init__(self, base_url="http://127.0.0.1:8000", timeout=30):
        self.base_url = base_url
        self.timeout = timeout
        self.ingest_url = f"{base_url}/api/openclaw/ingest"
        self.success_count = 0
        self.fail_count = 0
        self.failed_items = []

    def check_health(self):
        """检查服务健康状态"""
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
            return False

    def import_single(self, data: Dict, index: int = 0) -> bool:
        """导入单条数据"""
        payload_type = data.get("payload_type", "unknown")
        batch_id = data.get("batch_id", "unknown")

        try:
            response = requests.post(
                self.ingest_url,
                json=data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"  [{index}] ✓ {payload_type} ({batch_id})")
                    self.success_count += 1
                    return True
                else:
                    error_msg = result.get("message", "Unknown error")
                    print(f"  [{index}] ✗ {payload_type} ({batch_id}): {error_msg}")
                    self.fail_count += 1
                    self.failed_items.append({
                        "index": index,
                        "payload_type": payload_type,
                        "batch_id": batch_id,
                        "error": error_msg
                    })
                    return False
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print(f"  [{index}] ✗ {payload_type} ({batch_id}): HTTP {response.status_code} - {error_detail}")
                self.fail_count += 1
                self.failed_items.append({
                    "index": index,
                    "payload_type": payload_type,
                    "batch_id": batch_id,
                    "error": f"HTTP {response.status_code}: {error_detail}"
                })
                return False

        except Exception as e:
            print(f"  [{index}] ✗ {payload_type} ({batch_id}): {str(e)}")
            self.fail_count += 1
            self.failed_items.append({
                "index": index,
                "payload_type": payload_type,
                "batch_id": batch_id,
                "error": str(e)
            })
            return False

    def import_batch(self, data_list: List[Dict], delay: float = 0.1):
        """批量导入数据"""
        total = len(data_list)
        print(f"\n开始导入 {total} 条数据...")
        print("=" * 60)

        start_time = time.time()

        for i, data in enumerate(data_list, 1):
            self.import_single(data, i)
            if delay > 0 and i < total:
                time.sleep(delay)

        elapsed_time = time.time() - start_time

        print("=" * 60)
        print(f"\n导入完成！")
        print(f"  总计: {total} 条")
        print(f"  成功: {self.success_count} 条")
        print(f"  失败: {self.fail_count} 条")
        print(f"  耗时: {elapsed_time:.2f} 秒")
        print(f"  平均: {elapsed_time/total:.2f} 秒/条")

        if self.failed_items:
            print(f"\n失败详情:")
            for item in self.failed_items:
                print(f"  [{item['index']}] {item['payload_type']} ({item['batch_id']})")
                print(f"      错误: {item['error']}")

    def import_from_file(self, filepath: str, delay: float = 0.1):
        """从文件导入数据"""
        path = Path(filepath)
        if not path.exists():
            print(f"✗ 文件不存在: {filepath}")
            return False

        print(f"读取文件: {filepath}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                data_list = data
            elif isinstance(data, dict):
                data_list = [data]
            else:
                print(f"✗ 不支持的数据格式")
                return False

            print(f"✓ 读取到 {len(data_list)} 条数据")

            self.import_batch(data_list, delay)
            return True

        except json.JSONDecodeError as e:
            print(f"✗ JSON 解析错误: {e}")
            return False
        except Exception as e:
            print(f"✗ 读取文件失败: {e}")
            return False

    def save_failed_items(self, output_file="failed_items.json"):
        """保存失败的数据项"""
        if not self.failed_items:
            return

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.failed_items, f, ensure_ascii=False, indent=2)
        print(f"\n失败项已保存到: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenClaw 批量导入工具")
    parser.add_argument("file", help="要导入的 JSON 文件路径")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="服务地址 (默认: http://127.0.0.1:8000)")
    parser.add_argument("--delay", type=float, default=0.1, help="每条数据之间的延迟（秒）(默认: 0.1)")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时时间（秒）(默认: 30)")
    parser.add_argument("--no-health-check", action="store_true", help="跳过健康检查")
    parser.add_argument("--save-failed", action="store_true", help="保存失败的数据项到文件")

    args = parser.parse_args()

    print("=" * 60)
    print("OpenClaw 批量导入工具")
    print("=" * 60)

    importer = OpenClawBatchImporter(base_url=args.url, timeout=args.timeout)

    # 健康检查
    if not args.no_health_check:
        print("\n检查服务状态...")
        if not importer.check_health():
            print("\n服务不可用，请检查后端是否正常运行")
            return

    # 导入数据
    success = importer.import_from_file(args.file, delay=args.delay)

    # 保存失败项
    if args.save_failed and importer.failed_items:
        importer.save_failed_items()

    if success:
        print("\n✓ 导入流程完成")
    else:
        print("\n✗ 导入流程失败")


if __name__ == "__main__":
    main()
