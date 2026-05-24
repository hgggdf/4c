import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

try:
    import pymysql
    from config import get_settings
    s = get_settings()
    conn = pymysql.connect(
        host=s.mysql_host,
        port=s.mysql_port,
        user=s.mysql_user,
        password=s.mysql_password,
        charset='utf8mb4'
    )
    cur = conn.cursor()
    cur.execute(
        f'CREATE DATABASE IF NOT EXISTS `{s.mysql_database}` '
        f'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
    )
    conn.commit()
    conn.close()
    print(f'  数据库已就绪: {s.mysql_database}')
    sys.exit(0)
except Exception as e:
    print(f'  [错误] {e}')
    sys.exit(1)
