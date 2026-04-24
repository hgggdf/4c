import requests, json, re
from urllib.parse import quote

company = 'Jiangsu Hengrui Medicine Co Ltd'
query = quote(f'assignee:"{company}" country:CN after:2026-03-23')
url = f'https://patents.google.com/?q={query}&language=CHINESE&type=PATENT'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers, timeout=30)
    print('status:', r.status_code, 'len:', len(r.text))
    # 查找 script 中的 JSON 数据
    m = re.search(r'window\._ patentsData = ({.*?});', r.text, re.DOTALL)
    if m:
        print('found patents data!')
    else:
        print('no patents data found, first 500 chars:')
        print(r.text[:500])
except Exception as e:
    print('error:', e)
