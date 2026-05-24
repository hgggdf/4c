文件夹说明：backend/app/core/database/
====================
本文件夹为数据库层，负责数据库连接管理和 ORM 模型定义。

文件说明：
- base.py：SQLAlchemy 基类定义。
- init_db.py：数据库初始化脚本，创建表结构。
- session.py：数据库会话管理，提供连接池和事务控制。

子文件夹说明：
- models/：SQLAlchemy ORM 模型定义。
