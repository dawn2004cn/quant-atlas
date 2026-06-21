"""检查同步状态"""
import os
from dotenv import load_dotenv
load_dotenv()

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
    connect_timeout=30
)

try:
    with conn.cursor() as cur:
        for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
            cur.execute(f"SELECT COUNT(DISTINCT stock_code) FROM {table}")
            cnt = cur.fetchone()[0]
            cur.execute(f"SELECT MAX(date) FROM {table} WHERE date <= '2026-12-31'")
            max_date = cur.fetchone()[0]
            print(f"{table}: {cnt}只股票, 最新日期: {max_date}", flush=True)
finally:
    conn.close()

csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
print(f"\nCSV文件数: {len(csv_files)}", flush=True)