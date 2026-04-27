import sys, hashlib
sys.path.insert(0, r'C:\Users\chenyichang\Desktop\4c\backend')

from app.core.database.session import SessionLocal
from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.knowledge.store import _get_collection, ACTIVE_COLLECTIONS, chunk_text
from sqlalchemy import select

with SessionLocal() as db:
      # 先取前5条，看看实际有哪些 id
      rows = db.execute(select(AnnouncementRawHot).limit(5)).scalars().all()
      for r in rows:
          print(f'id={r.id}  title={r.title}')
      row = db.execute(select(AnnouncementRawHot).where(AnnouncementRawHot.id == 1346)).scalars().first()

      content = (row.content or '').strip()
      print('DB row id:', row.id)
      print('title:', row.title)
      print('content[:80]:', content[:80])

      doc_id = f'announcement_{row.id}_{hashlib.md5(content[:200].encode()).hexdigest()[:10]}'
      chunks = chunk_text(content)
      print('chunk count:', len(chunks))

      expected_ids = [
          hashlib.md5(f'{doc_id}_{i}_{c}'.encode()).hexdigest()
          for i, c in enumerate(chunks)
      ]
      col = _get_collection(ACTIVE_COLLECTIONS['announcement'])
      result = col.get(ids=expected_ids, include=[])
      print('found in Chroma:', len(result.get('ids', [])), '/', len(chunks))