import time
from crawler.clients.cnipa_client import CnipaClient

client = CnipaClient()
for code, name in [('600276', '恒瑞医药'), ('603259', '药明康德'), ('300832', '新产业'), ('600998', '九州通')]:
    start = time.time()
    result = client.fetch_patent_announcements(code, name, begin_date='2026-03-24', end_date='2026-04-23')
    elapsed = time.time() - start
    success = result['success']
    count = result['data']['patent_announcements_count']
    print(f'{code}: {elapsed:.1f}s, success={success}, count={count}')
