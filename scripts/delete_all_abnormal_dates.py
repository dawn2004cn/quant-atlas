"""删除stock_history_sh表中所有异常日期数据"""
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
        print("\n查找所有异常日期数据...", flush=True)
        cur.execute("SELECT date, COUNT(*) FROM stock_history_sh GROUP BY date HAVING date > '2026-12-31'")
        results = cur.fetchall()
        print(f"找到 {len(results)} 个异常日期:", flush=True)
        for date, count in results:
            print(f"  {date}: {count} 条")
        
        print("\n删除所有异常日期数据...", flush=True)
        cur.execute("DELETE FROM stock_history_sh WHERE date > '2026-12-31'")
        print(f"已删除 {cur.rowcount} 条记录", flush=True)
        
        print("\n验证删除结果:", flush=True)
        cur.execute("SELECT MAX(date) FROM stock_history_sh")
        max_date = cur.fetchone()[0]
        print(f"最新日期: {max_date}", flush=True)
        
        cur.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_history_sh")
        cnt = cur.fetchone()[0]
        print(f"股票数量: {cnt}", flush=True)

finally:
    conn.close()

print("\n操作完成!", flush=True)
