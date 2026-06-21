"""快速删除异常日期"""
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
        # 删除所有非正常年份的数据
        cur.execute("DELETE FROM stock_history_sh WHERE date > '2026-12-31' OR date < '2000-01-01' LIMIT 1000")
        print(f"删除: {cur.rowcount}", flush=True)
        cur.execute("SELECT MAX(date) FROM stock_history_sh WHERE date <= '2026-12-31'")
        print(f"最新: {cur.fetchone()[0]}", flush=True)
finally:
    conn.close()