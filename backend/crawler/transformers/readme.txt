文件夹说明：backend/crawler/transformers/
====================
本文件夹为数据转换器模块，将爬取的原始数据转换为系统标准格式。

文件说明：
- base.py：转换器基类，定义通用转换接口。
- announcement_transformer.py：公告数据转换器。
- company_transformer.py：公司数据转换器。
- macro_transformer.py：宏观经济数据转换器。
- patent_transformer.py：专利数据转换器。
- research_report_transformer.py：研报数据转换器。
- stock_daily_transformer.py：股票日线数据转换器。
- run_transform.py：转换任务执行入口脚本。
