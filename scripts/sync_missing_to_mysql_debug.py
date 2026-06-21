"""调试版同步脚本"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

print("=== 开始同步任务 ===")
start_time = time.time()

settings = get_settings()
print(f"MySQL配置: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}")

# 获取CSV中的股票代码
print("\n1. 读取CSV文件列表...")
csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
csv_codes = {f.stem for f in csv_files}
print(f"CSV股票数: {len(csv_codes)}")

# 获取已同步到MySQL的股票代码
print("\n2. 连接MySQL获取已同步股票...")
conn = pymysql.connect(
    host=settings.mysql.host,
    port=settings.mysql.port,
    user=settings.mysql.user,
    password=settings.mysql.password,
    db=settings.mysql.database,
    connect_timeout=30
)
mysql_codes = set()
try:
    with conn.cursor() as cur:
        for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
            print(f"  查询表: {table}...")
            try:
                cur.execute(f"SELECT DISTINCT stock_code FROM {table}")
                for row in cur.fetchall():
                    if row[0]:
                        mysql_codes.add(str(row[0]).upper())
            except Exception as e:
                print(f"    表 {table} 错误: {e}")
finally:
    conn.close()

print(f"MySQL股票数: {len(mysql_codes)}")

# 找出缺失的股票
missing = sorted(list(csv_codes - mysql_codes))
print(f"\n3. 缺失股票数: {len(missing)}")
if missing:
    print(f"   前10只缺失股票: {missing[:10]}")

print(f"\n=== 准备阶段完成，耗时 {time.time() - start_time:.2f} 秒 ===")
