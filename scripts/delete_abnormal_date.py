"""删除stock_history_sh表中的异常日期数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

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
        print("\n查找异常日期数据...", flush=True)
        cur.execute("SELECT COUNT(*) FROM stock_history_sh WHERE date = '8636-15-74'")
        count = cur.fetchone()[0]
        print(f"找到 {count} 条异常日期数据", flush=True)
        
        if count > 0:
            print("\n删除异常数据...", flush=True)
            cur.execute("DELETE FROM stock_history_sh WHERE date = '8636-15-74'")
            print(f"已删除 {cur.rowcount} 条记录", flush=True)
        
        print("\n验证删除结果:", flush=True)
        cur.execute("SELECT COUNT(*) FROM stock_history_sh WHERE date = '8636-15-74'")
        remaining = cur.fetchone()[0]
        print(f"剩余异常数据: {remaining}", flush=True)
        
        cur.execute("SELECT MAX(date) FROM stock_history_sh")
        max_date = cur.fetchone()[0]
        print(f"最新日期: {max_date}", flush=True)
        
        cur.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_history_sh")
        cnt = cur.fetchone()[0]
        print(f"股票数量: {cnt}", flush=True)

finally:
    conn.close()

print("\n操作完成!", flush=True)
