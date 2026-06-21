"""多线程快速同步脚本 - 使用批量插入和线程池"""
import sys
import gc
import csv
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def sync_stock_chunk(stock_codes, settings, csv_dir):
    """同步一批股票数据"""
    conn = None
    cur = None
    try:
        conn = create_connection(settings)
        cur = conn.cursor()
        
        synced = 0
        failed = []
        
        for stock_code in stock_codes:
            csv_path = csv_dir / f"{stock_code.lower()}.csv"
            if not csv_path.exists():
                continue
            
            try:
                rows = []
                with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    has_stock_code = header and 'stock_code' in ','.join(header).lower()
                    for row in reader:
                        if len(row) >= 7:
                            try:
                                if has_stock_code:
                                    rows.append((
                                        stock_code.lower(),
                                        row[1] if len(row) > 1 else '',
                                        float(row[2]) if row[2] else 0,
                                        float(row[3]) if row[3] else 0,
                                        float(row[4]) if row[4] else 0,
                                        float(row[5]) if row[5] else 0,
                                        float(row[6]) if row[6] else 0,
                                        float(row[7]) if row[7] else 0,
                                    ))
                                else:
                                    rows.append((
                                        stock_code.lower(),
                                        row[0] if len(row) > 0 else '',
                                        float(row[1]) if row[1] else 0,
                                        float(row[2]) if row[2] else 0,
                                        float(row[3]) if row[3] else 0,
                                        float(row[4]) if row[4] else 0,
                                        float(row[5]) if row[5] else 0,
                                        float(row[6]) if row[6] else 0,
                                    ))
                            except (ValueError, IndexError):
                                pass
                
                if rows:
                    table = f"stock_history_{stock_code.lower()[:2]}"
                    placeholders = ','.join(['%s'] * 8)
                    sql = f"INSERT IGNORE INTO {table} (stock_code, date, open, high, low, close, volume, amount) VALUES ({placeholders})"
                    cur.executemany(sql, rows)
                del rows
                gc.collect()
                synced += 1
            except Exception as e:
                failed.append((stock_code, str(e)[:50]))
        
        return synced, failed
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

print("=== 多线程快速同步任务 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
csv_codes = {f.stem.upper() for f in csv_files}
print(f"\nCSV总数: {len(csv_codes)}", flush=True)

print("\n获取MySQL已同步股票...", flush=True)
conn = create_connection(settings)
cur = conn.cursor()

synced_codes = set()
for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
    try:
        cur.execute(f"SELECT DISTINCT stock_code FROM {table}")
        for row in cur.fetchall():
            if row[0]:
                synced_codes.add(str(row[0]).upper())
    except:
        pass

cur.close()
conn.close()
print(f"MySQL已同步: {len(synced_codes)}", flush=True)

missing = sorted(list(csv_codes - synced_codes))
print(f"待同步: {len(missing)}", flush=True)

if not missing:
    print("全部完成!", flush=True)
    sys.exit(0)

print(f"前5只: {missing[:5]}", flush=True)

print("\n开始同步（多线程模式）...", flush=True)
total = len(missing)
num_workers = 8
chunk_size = (total // num_workers) + 1
chunks = [missing[i:i+chunk_size] for i in range(0, total, chunk_size)]

print(f"使用 {num_workers} 个线程，每线程处理 {chunk_size} 只股票", flush=True)

total_synced = 0
total_failed = []

with ThreadPoolExecutor(max_workers=num_workers) as executor:
    futures = []
    for i, chunk in enumerate(chunks):
        futures.append((i, executor.submit(sync_stock_chunk, chunk, settings, csv_dir)))
    
    for i, future in futures:
        synced, failed = future.result()
        total_synced += synced
        total_failed.extend(failed)
        elapsed = time.time() - start_time
        speed = total_synced / elapsed if elapsed > 0 else 0
        print(f"  线程 {i+1}/{num_workers} 完成: {synced} 成功", flush=True)

print("\n=== 同步完成 ===", flush=True)
print(f"成功: {total_synced}, 失败: {len(total_failed)}", flush=True)
print(f"耗时: {time.time() - start_time:.2f}秒", flush=True)
print(f"平均速度: {total_synced / (time.time() - start_time):.1f}只/秒", flush=True)
if total_failed:
    print(f"失败列表: {total_failed[:5]}", flush=True)
