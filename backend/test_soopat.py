import requests
from urllib.parse import quote

# SOOPAT 搜索
company = "江苏恒瑞医药股份有限公司"
query = quote(company)
url = f"http://www.soopat.com/Home/Result?SearchWord={query}&PatentIndex=0&Valid=2"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

try:
    r = requests.get(url, headers=headers, timeout=30)
    print("status:", r.status_code, "len:", len(r.text))
    print("first 1000 chars:")
    print(r.text[:1000])
except Exception as e:
    print("error:", e)
