文件夹说明：backend/crawler/staging/
====================
本文件夹为数据暂存目录，存放经过转换后待入库的数据文件和打包文件。

文件说明：
- announcement_package.json：公告数据打包文件。
- company_package.json：公司数据打包文件。
- stock_daily_package.json：股票日线数据打包文件。

子文件夹说明：
- announcement/：转换后的公告数据。
- company/：转换后的公司数据。
- e2e/：端到端测试暂存数据。
- financial/：转换后的财务数据。
- macro/：转换后的宏观经济数据。
- macro_phasec_live/：宏观经济 Phase C 实时数据。
- news/：转换后的新闻数据。
- quality_reports/：数据质量报告。
- research_reports_phasec_live/：研报 Phase C 实时数据。
- stock_daily/：转换后的股票日线数据。
- stress/：压力测试数据。
- stress_200/：200 条压力测试数据。
