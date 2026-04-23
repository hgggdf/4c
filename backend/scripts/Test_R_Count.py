import sys, os
sys.path.insert(0, r'C:\Users\chenyichang\Desktop\4c\backend')
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from app.knowledge.store import get_vector_store

vs = get_vector_store()

  # 1. 计数
print("=== 计数 ===")
for dt in ['announcement', 'financial_note', 'company_profile', 'news']:
      print(f'{dt}: {vs.count(doc_type=dt)}')

  # 2. 语义检索（改关键词和股票代码）
print("\n=== 检索 ===")
results = vs.search('年报', top_k=5, doc_types=['announcement'], filters={'stock_code': '600276'})
for r in results:
      m = r['meta']
      print(f"score={r['score']:.3f}  {m.get('publish_date')}  {m.get('title','')[:50]}")