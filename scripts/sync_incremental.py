"""快速同步增量数据到MySQL（2026-06-09到2026-06-12）"""
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

print("=== 增量同步到 2026-06-12 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
print(f"CSV文件数: {len(csv_files)}", flush=True)

conn = create_connection(settings)
cur = conn.cursor()

print("\n同步增量数据（2026-06-09 到 2026-06-12）...", flush=True)

synced = 0
total_rows = 0

for i, csv_file in enumerate(csv_files, 1):
    stock_code = csv_file.stem.upper()
    table = f"stock_history_{stock_code.lower()[:2]}"
    
    try:
        rows = []
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            has_stock_code = header and 'stock_code' in ','.join(header).lower()
            for row in reader:
                if len(row) >= 7:
                    try:
                        if has_stock_code:
                            date_val = row[1] if len(row) > 1 else ''
                        else:
                            date_val = row[0] if len(row) > 0 else ''
                        
                        if date_val >= '2026-06-09' and date_val <= '2026-06-12':
                            if has_stock_code:
                                rows.append((
                                    stock_code.lower(),
                                    date_val,
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
                                    date_val,
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
            placeholders = ','.join(['%s'] * 8)
            sql = f"INSERT IGNORE INTO {table} (stock_code, date, open, high, low, close, volume, amount) VALUES ({placeholders})"
            cur.executemany(sql, rows)
            total_rows += len(rows)
        del rows
        gc.collect()
        synced += 1
        
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f"  进度: {i}/{len(csv_files)}, 已同步行数: {total_rows}", flush=True)

    except Exception as e:
        print(f"  失败 {stock_code}: {str(e)[:50]}", flush=True)

conn.close()

print("\n=== 同步完成 ===", flush=True)
print(f"成功同步: {synced}只股票, {total_rows}行数据", flush=True)
print(f"耗时: {time.time() - start_time:.2f}秒", flush=True)
