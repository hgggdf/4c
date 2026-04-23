import requests
import re

url = "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=300122&announcementId=1225226087&orgId=gssz0300122&announcementTime=2026-04-07"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
}

r = requests.get(url, headers=headers, timeout=30)
text = r.text

# Search for PDF URL
pdf_match = re.search(r'href="(https?://[^"]+\.pdf)"', text, re.IGNORECASE)
if pdf_match:
    print("PDF URL:", pdf_match.group(1))
else:
    # Search for iframe src
    iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', text, re.IGNORECASE)
    if iframe_match:
        print("iframe src:", iframe_match.group(1))
    else:
        print("No PDF or iframe found")
        # Look for any URL patterns
        urls = re.findall(r'https?://[^\s\"<>]+', text)
        for u in urls[:20]:
            if 'pdf' in u.lower() or 'download' in u.lower() or 'file' in u.lower():
                print("possible URL:", u)
