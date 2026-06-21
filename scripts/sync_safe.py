"""安全同步脚本 - 使用更保守的内存管理和错误处理"""
import sys
import gc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql
import pandas as pd
import time

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

print("=== 安全同步任务 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

# 获取CSV中的股票代码
print("\n1. 读取CSV列表...", flush=True)
csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
csv_codes = {f.stem.upper() for f in csv_files}
print(f"CSV总数: {len(csv_codes)}", flush=True)

# 获取MySQL已同步的股票
print("\n2. 获取MySQL已同步股票...", flush=True)
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

# 找出缺失的股票
missing = sorted(list(csv_codes - synced_codes))
print(f"待同步: {len(missing)}", flush=True)

if not missing:
    print("全部完成!", flush=True)
    sys.exit(0)

print(f"前5只: {missing[:5]}", flush=True)

print("\n3. 开始同步（安全模式）...", flush=True)
total = len(missing)
synced = 0
failed = []
skipped = 0

conn = create_connection(settings)
cur = conn.cursor()

for i, stock_code in enumerate(missing, 1):
    csv_path = csv_dir / f"{stock_code.lower()}.csv"
    if not csv_path.exists():
        skipped += 1
        continue

    try:
        # 使用更小的块大小读取CSV
        df_chunks = []
        try:
            for chunk in pd.read_csv(csv_path, chunksize=500, on_bad_lines='skip'):
                chunk['stock_code'] = stock_code.lower()
                df_chunks.append(chunk)
                # 每读取一块就立即写入
                table = f"stock_history_{stock_code.lower()[:2]}"
                columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                placeholders = ','.join(['%s'] * len(columns))
                sql = f"INSERT IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                data = [tuple(row) for row in chunk[columns].values]
                cur.executemany(sql, data)
                del chunk
                gc.collect()
        except Exception as e:
            # 如果分块读取失败，尝试整文件读取
            try:
                df = pd.read_csv(csv_path, on_bad_lines='skip')
                df['stock_code'] = stock_code.lower()
                table = f"stock_history_{stock_code.lower()[:2]}"
                columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                placeholders = ','.join(['%s'] * len(columns))
                sql = f"INSERT IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                data = [tuple(row) for row in df[columns].values]
                cur.executemany(sql, data)
                del df, data
            except Exception as e2:
                raise Exception(f"both methods failed: {str(e)[:30]}, {str(e2)[:30]}")

        del df_chunks
        gc.collect()

        synced += 1

        if i % 50 == 0:
            elapsed = time.time() - start_time
            speed = synced / elapsed if elapsed > 0 else 0
            print(f"   进度: {synced}/{total} ({(i/total)*100:.1f}%), 速度: {speed:.1f}只/秒", flush=True)

    except Exception as e:
        failed.append((stock_code, str(e)[:50]))
        if len(failed) <= 10:
            print(f"   FAIL {stock_code}: {str(e)[:50]}", flush=True)

conn.close()

print("\n=== 同步完成 ===", flush=True)
print(f"成功: {synced}, 跳过: {skipped}, 失败: {len(failed)}", flush=True)
print(f"耗时: {time.time() - start_time:.2f}秒", flush=True)
if failed:
    print(f"失败列表: {failed[:10]}", flush=True)
