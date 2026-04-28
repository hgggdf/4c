import subprocess
import time
import requests
import os
import json

# ============ 【配置项】 ============
SSH_COMMAND = [
    "ssh", "-L", "8900:localhost:8900",
    "admin@8.219.129.250", "-N"
]

# 你的本地保存路径
LOCAL_SAVE_ROOT = r"E:\新建文件夹\4c\backend\data\incoming"

# 最新数据包目录
BASE_URL = "data/incoming/today"

# 完全匹配最新目录结构
DIRS = {
    "company": "company_records.jsonl",
    "financial": "financial_records.jsonl",
    "announcement": "announcement_records.jsonl",
    "research_report": "research_report_records.jsonl",
    "news": "news_records.jsonl",
    "macro": "macro_records.jsonl",
}

WAIT_SECONDS = 3
# ====================================

def download_file(relative_url, local_path):
    full_url = f"http://localhost:8900/{relative_url}"
    full_local_path = os.path.join(LOCAL_SAVE_ROOT, local_path)

    try:
        # ✅ 修复：正确写法 os.path.dirname
        os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
        print(f"⬇️  下载: {relative_url}")

        resp = requests.get(full_url, stream=True, timeout=30)
        resp.raise_for_status()

        with open(full_local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ 保存: {full_local_path}\n")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}\n")
        return False

def main():
    print("🔌 启动 SSH 隧道...")
    tunnel = subprocess.Popen(SSH_COMMAND)
    time.sleep(WAIT_SECONDS)

    try:
        print("=" * 50)
        print("📦 下载批次清单")
        print("=" * 50)
        download_file(
            f"{BASE_URL}/manifest.json",
            "today/manifest.json"
        )

        for dir_name, jsonl_name in DIRS.items():
            print("=" * 50)
            print(f"📂 处理目录: {dir_name}")
            print("=" * 50)

            jsonl_url = f"{BASE_URL}/{dir_name}/{jsonl_name}"
            jsonl_local = f"today/{dir_name}/{jsonl_name}"
            download_file(jsonl_url, jsonl_local)

            jsonl_path = os.path.join(LOCAL_SAVE_ROOT, jsonl_local)
            if not os.path.exists(jsonl_path):
                print(f"⚠️ {dir_name} 无附件，跳过\n")
                continue

            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    
                    # ✅ 严格过滤 None / 空值
                    if rec.get("local_file"):
                        file_url = f"{BASE_URL}/{dir_name}/{rec['local_file']}"
                        file_local = f"today/{dir_name}/{rec['local_file']}"
                        download_file(file_url, file_local)

        print("🎉" * 5 + " 全部数据下载完成！" + "🎉" * 5)

    finally:
        tunnel.terminate()
        print("\n🔌 隧道已安全关闭")

if __name__ == "__main__":
    main()