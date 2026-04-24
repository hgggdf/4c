import akshare as ak
from datetime import datetime, timedelta

companies = ['600276', '300676', '603259', '300760']
patent_keywords = ['专利', '发明', '实用新型', '外观设计', '知识产权']

for code in companies:
    begin = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    end = datetime.now().strftime('%Y-%m-%d')
    try:
        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code,
            start_date=begin.replace('-', ''),
            end_date=end.replace('-', '')
        )
        mask = df['公告标题'].str.contains('|'.join(patent_keywords), na=False)
        patent_df = df[mask]
        print(f'{code}: total={len(df)}, patent_related={len(patent_df)}')
        for _, row in patent_df.head(3).iterrows():
            print(f'  - {row["公告标题"]} ({row["公告时间"]})')
    except Exception as e:
        print(f'{code}: error {type(e).__name__}: {e}')
