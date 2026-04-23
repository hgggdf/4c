import requests
from urllib.parse import quote
import re

company = "江苏恒瑞医药股份有限公司"
url = f"https://www.tianyancha.com/search?key={quote(company)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.tianyancha.com/",
}

r = requests.get(url, headers=headers, timeout=30)
print("status:", r.status_code, "len:", len(r.text))

# Check for company link
m = re.search(r'href="(https://www\.tianyancha\.com/company/\d+)"', r.text)
if m:
    print("found company link:", m.group(1))
else:
    print("no company link found")
    # Look for any JSON data in script tags
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
    for s in scripts:
        if "company" in s.lower() and len(s) > 100:
            print("script snippet:", s[:500])
            break
