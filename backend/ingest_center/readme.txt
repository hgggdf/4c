文件夹说明：backend/ingest_center/
====================
本文件夹为数据入库中心，负责将转换后的数据导入数据库和向量存储。

文件说明：
- hot_archive_service.py：热数据归档服务，管理热点数据的归档策略。
- import_worker.py：导入工作器，执行实际的数据入库操作。
