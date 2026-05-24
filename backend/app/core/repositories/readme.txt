文件夹说明：backend/app/core/repositories/
====================
本文件夹为数据仓储层，封装对数据库的 CRUD 操作，为服务层提供数据访问接口。

文件说明：
- base.py：仓储基类，定义通用的增删改查方法。
- announcement_repository.py：公告数据读取仓储。
- announcement_write_repository.py：公告数据写入仓储。
- cache_repository.py：缓存仓储，管理查询缓存。
- chat_repository.py：对话记录仓储。
- company_repository.py：公司数据读取仓储。
- company_write_repository.py：公司数据写入仓储。
- financial_repository.py：财务数据读取仓储。
- financial_write_repository.py：财务数据写入仓储。
- macro_repository.py：宏观经济数据读取仓储。
- macro_write_repository.py：宏观经济数据写入仓储。
- maintenance_repository.py：系统维护仓储。
- news_repository.py：新闻数据读取仓储。
- news_write_repository.py：新闻数据写入仓储。
- research_report_repository.py：研报数据读取仓储。
- research_report_write_repository.py：研报数据写入仓储。
