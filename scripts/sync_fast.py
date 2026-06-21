"""快速同步脚本 - 直接同步所有CSV到MySQL，使用INSERT IGNORE"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

def create_connection(settings):
    """创建MySQL连接"""
    return pymysql.connect(
        host=settings.mysql.host,
        port=settings.mysql.port,
        user=settings.mysql.user,
        password=settings.mysql.password,
        db=settings.mysql.database,
        connect_timeout=30,
        autocommit=True
    )

print("=== 开始快速同步任务 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL配置: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

# 获取CSV中的股票代码
print("\n1. 读取CSV文件列表...", flush=True)
csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
print(f"CSV文件数: {len(csv_files)}", flush=True)

print("\n2. 开始导入pandas...", flush=True)
import pandas as pd
print("   导入完成", flush=True)

print("\n3. 创建MySQL连接...", flush=True)
conn = create_connection(settings)
cur = conn.cursor()

print("\n4. 开始同步数据...", flush=True)
total = len(csv_files)
synced = 0
failed = []
batch_size = 100
start_sync = time.time()

for i, csv_path in enumerate(csv_files, 1):
    stock_code = csv_path.stem.upper()
    
    try:
        if conn is None or not conn.open:
            print(f"   重新连接MySQL...", flush=True)
            conn = create_connection(settings)
            cur = conn.cursor()
        
        df = pd.read_csv(csv_path)
        table = f"stock_history_{stock_code.lower()[:2]}"
        
        df['stock_code'] = stock_code.lower()
        
        columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        placeholders = ','.join(['%s'] * len(columns))
        sql = f"INSERT IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        
        data = [tuple(row) for row in df[columns].values]
        cur.executemany(sql, data)
        
        synced += 1
        
        if i % batch_size == 0:
            elapsed = time.time() - start_sync
            speed = synced / elapsed if elapsed > 0 else 0
            print(f"   已同步: {synced}/{total} ({(i/total)*100:.1f}%), 速度: {speed:.1f} 只/秒", flush=True)
            
    except Exception as e:
        failed.append((stock_code, str(e)))
        if conn:
            try:
                conn.close()
            except:
                pass
        conn = None
        cur = None
        if len(failed) <= 5:
            print("   FAIL " + stock_code + ": " + str(e)[:50], flush=True)

if conn:
    conn.close()

print("\n=== 同步完成 ===", flush=True)
print(f"成功: {synced}, 失败: {len(failed)}", flush=True)
print(f"总耗时: {time.time() - start_time:.2f} 秒", flush=True)
if failed:
    print("失败列表前5个:", failed[:5], flush=True)
