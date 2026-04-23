import requests
from urllib.parse import quote

# 企查查搜索
company = "江苏恒瑞医药股份有限公司"
query = quote(company)
url = f"https://www.qcc.com/web/search?key={query}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.qcc.com/",
}

try:
    r = requests.get(url, headers=headers, timeout=30)
    print("status:", r.status_code, "len:", len(r.text))
    print("first 1500 chars:")
    print(r.text[:1500])
except Exception as e:
    print("error:", e)
