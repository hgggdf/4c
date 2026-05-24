文件夹说明：backend/app/router/
====================
本文件夹为 API 路由层，定义所有 HTTP 接口端点，处理请求参数校验和响应格式化。

文件说明：
- agent.py：智能体对话接口。
- analysis.py：分析功能接口。
- analysis_service.py：分析服务辅助模块。
- announcement.py：公告查询接口。
- announcement_write.py：公告写入接口。
- butterfly.py：蝴蝶效应分析接口。
- cache.py：缓存管理接口。
- chat.py：聊天对话接口。
- chat_service.py：聊天服务辅助模块。
- company.py：公司信息查询接口。
- company_write.py：公司信息写入接口。
- dependencies.py：依赖注入定义。
- doc.py：文档相关接口。
- financial.py：财务数据查询接口。
- financial_write.py：财务数据写入接口。
- ingest.py：数据入库接口。
- macro.py：宏观经济数据查询接口。
- macro_write.py：宏观经济数据写入接口。
- maintenance.py：系统维护接口。
- news.py：新闻查询接口。
- news_write.py：新闻写入接口。
- openclaw_ingest.py：OpenClaw 数据入库接口。
- query.py：通用查询接口。
- retrieval.py：语义检索接口。
- shared.py：共享工具函数。
- stock.py：股票数据接口。
- stock_service.py：股票服务辅助模块。
- utils.py：路由层工具函数。

子文件夹说明：
- schemas/：请求和响应的数据模式定义。
