"""简单的批量同步脚本 - 每50只输出进度"""
import sys
import gc
import csv
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

def create_connection(settings):
    return pymysql.connect(
        host=settings.mysql.host,
        port=settings.mysql.port,
        user=settings.mysql.user,
        password=settings.mysql.password,
        db=settings.mysql.database,
        connect_timeout=30,
        autocommit=True
    )

print("=== 批量同步任务 ===", flush=True)
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
total = len(missing)
print(f"待同步: {total}", flush=True)

if not missing:
    print("全部完成!", flush=True)
    sys.exit(0)

print(f"\n开始同步...", flush=True)

conn = create_connection(settings)
cur = conn.cursor()

synced = 0
failed = []
skipped = 0

for i, stock_code in enumerate(missing, 1):
    csv_path = csv_dir / f"{stock_code.lower()}.csv"
    if not csv_path.exists():
        skipped += 1
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
            # 使用executemany
            cur.executemany(sql, rows)
        del rows
        gc.collect()
        synced += 1

        if i % 50 == 0:
            elapsed = time.time() - start_time
            speed = synced / elapsed if elapsed > 0 else 0
            remaining = total - i
            eta = remaining / speed if speed > 0 else 0
            print(f"  进度: {i}/{total} ({(i/total)*100:.1f}%), 速度: {speed:.1f}只/秒, 剩余: {eta:.0f}秒", flush=True)

    except Exception as e:
        failed.append((stock_code, str(e)[:80]))
        if len(failed) <= 3:
            print(f"  失败 {stock_code}: {str(e)[:80]}", flush=True)

conn.close()

print("\n=== 同步完成 ===", flush=True)
print(f"成功: {synced}, 跳过: {skipped}, 失败: {len(failed)}", flush=True)
print(f"耗时: {time.time() - start_time:.2f}秒", flush=True)
if failed:
    print(f"失败列表: {failed[:5]}", flush=True)
