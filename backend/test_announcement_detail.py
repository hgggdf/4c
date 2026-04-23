import requests
from bs4 import BeautifulSoup

# 智飞生物专利公告详情页
url = "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=300122&announcementId=1225226087&orgId=gssz0300122&announcementTime=2026-04-07"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
}

try:
    r = requests.get(url, headers=headers, timeout=30)
    print("status:", r.status_code, "len:", len(r.text))
    soup = BeautifulSoup(r.text, "html.parser")
    # Find main content
    content_div = soup.find("div", class_="detail-body") or soup.find("div", {"id": "noticeContent"}) or soup.find("div", class_="main")
    if content_div:
        text = content_div.get_text(strip=True)
        print("content preview:", text[:500])
    else:
        print("no content div found, first 1000 chars:")
        print(r.text[:1000])
except Exception as e:
    print("error:", e)
