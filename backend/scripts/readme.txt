文件夹说明：backend/scripts/
====================
本文件夹存放运维和数据处理脚本，用于数据回填、导入和索引维护等操作。

文件说明：
- backfill_vector_store.py：向量存储回填脚本，将历史数据补充到向量数据库。
- fast_backfill.py：快速回填脚本，优化的批量回填实现。
- import_local_data.py：本地数据导入脚本。
- import_research_reports.py：研报数据导入脚本。
- quick_import_local_data.py：快速本地数据导入脚本。
- rebuild_announcement_collection.py：重建公告向量集合脚本。
- rebuild_research_report_collection.py：重建研报向量集合脚本。
- verify_vector_index.py：向量索引验证脚本，检查索引完整性。
