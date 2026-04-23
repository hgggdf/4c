"""
ingest_center
===========

入库中心独立模块。

职责：
    读取 OpenClaw 产出的 manifest 与 staging 数据，经校验后通过 HTTP 调用现有后端接口完成入库。

当前阶段：
    仅建立目录骨架与文件模板，不实现具体业务逻辑。
"""
