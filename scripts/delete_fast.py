"""快速删除异常日期数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

settings = get_settings()
conn = pymysql.connect(
    host=settings.mysql.host,
    port=settings.mysql.port,
    user=settings.mysql.user,
    password=settings.mysql.password,
    db=settings.mysql.database,
    connect_timeout=30,
    autocommit=True
)

try:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM stock_history_sh WHERE date = '2041-90-51'")
        print(f"已删除 {cur.rowcount} 条记录", flush=True)
        cur.execute("SELECT MAX(date) FROM stock_history_sh")
        print(f"最新日期: {cur.fetchone()[0]}", flush=True)
finally:
    conn.close()

print("完成!", flush=True)
