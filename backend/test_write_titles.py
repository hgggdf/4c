import akshare as ak
from datetime import datetime, timedelta

codes = ['300122', '300832', '600998']
begin = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')

with open('test_titles2.txt', 'w', encoding='utf-8') as f:
    for code in codes:
        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code,
            start_date=begin.replace('-', ''),
            end_date=end.replace('-', '')
        )
        mask = df['公告标题'].str.contains('专利|发明|实用新型|外观设计|知识产权', na=False)
        for _, row in df[mask].iterrows():
            f.write(f'{code}: {row["公告标题"]}\n')
