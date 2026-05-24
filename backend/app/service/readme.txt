文件夹说明：backend/app/service/
====================
本文件夹为业务逻辑服务层，封装核心业务逻辑，协调仓储层和外部服务。

文件说明：
- base.py：服务基类定义。
- container.py：依赖注入容器，管理服务实例的创建和生命周期。
- context.py：请求上下文管理。
- dto.py：数据传输对象定义。
- exceptions.py：业务异常定义。
- guards.py：权限守卫，控制接口访问权限。
- requests.py：服务层请求对象。
- write_requests.py：写入操作请求对象。
- serializers.py：数据序列化工具。
- announcement_service.py：公告查询服务。
- announcement_write_service.py：公告写入服务。
- butterfly_service.py：蝴蝶效应分析服务。
- cache_service.py：缓存管理服务。
- chat_service.py：聊天对话服务。
- company_service.py：公司信息查询服务。
- company_write_service.py：公司信息写入服务。
- doc_image_service.py：文档图片处理服务。
- financial_service.py：财务数据查询服务。
- financial_write_service.py：财务数据写入服务。
- ingest_gateway_service.py：数据入库网关服务。
- macro_service.py：宏观经济数据查询服务。
- macro_write_service.py：宏观经济数据写入服务。
- maintenance_service.py：系统维护服务。
- news_service.py：新闻查询服务。
- news_write_service.py：新闻写入服务。
- research_report_write_service.py：研报写入服务。
- retrieval_service.py：语义检索服务。

子文件夹说明：
- adapters/：服务适配器，对接外部系统（缓存、向量存储等）。
