"""从通达信同步最新数据到MySQL和CSV"""
import os
from dotenv import load_dotenv
load_dotenv()

import sys
import struct
import csv
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

tdx_root = Path(r'E:\tdx\通达信金融终端(开心果交易版)V2024.02')
day_dir = tdx_root / 'vipdoc'

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

def read_tdx_day_file(file_path):
    """读取通达信.day文件"""
    rows = []
    with open(file_path, 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()
        num_records = file_size // 32
        
        f.seek(0)
        for _ in range(num_records):
            data = f.read(32)
            if len(data) == 32:
                date_int = struct.unpack('<I', data[0:4])[0]
                if date_int > 19900101 and date_int < 21000101:
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    
                    open_price = struct.unpack('<I', data[4:8])[0] / 100.0
                    high_price = struct.unpack('<I', data[8:12])[0] / 100.0
                    low_price = struct.unpack('<I', data[12:16])[0] / 100.0
                    close_price = struct.unpack('<I', data[16:20])[0] / 100.0
                    amount = struct.unpack('<f', data[20:24])[0]
                    volume = struct.unpack('<I', data[24:28])[0]
                    
                    rows.append((date_str, open_price, high_price, low_price, close_price, volume, amount))
    return rows

def sync_stock(file_path, settings, csv_dir, min_date):
    """同步单只股票"""
    stock_code = file_path.stem.lower()
    table = f"stock_history_{stock_code[:2]}"
    
    rows = read_tdx_day_file(file_path)
    if not rows:
        return 0, 0
    
    # 筛选增量数据
    new_rows = [r for r in rows if r[0] > min_date]
    if not new_rows:
        return 0, 0
    
    # 写入MySQL
    conn = create_connection(settings)
    cur = conn.cursor()
    
    mysql_rows = []
    for r in new_rows:
        mysql_rows.append((
            stock_code,
            r[0],  # date
            r[1],  # open
            r[2],  # high
            r[3],  # low
            r[4],  # close
            r[5],  # volume
            r[6],  # amount
        ))
    
    placeholders = ','.join(['%s'] * 8)
    sql = f"INSERT IGNORE INTO {table} (stock_code, date, open, high, low, close, volume, amount) VALUES ({placeholders})"
    cur.executemany(sql, mysql_rows)
    mysql_count = cur.rowcount
    
    cur.close()
    conn.close()
    
    # 写入CSV
    csv_path = csv_dir / f"{stock_code}.csv"
    existing_rows = []
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= 8:
                    existing_rows.append(row)
    
    # 合并新旧数据
    all_rows = set()
    for r in existing_rows:
        all_rows.add((r[0], r[1]))  # (stock_code, date)
    for r in new_rows:
        all_rows.add((stock_code, r[0]))
    
    # 写入CSV
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
        for r in rows:
            writer.writerow([stock_code, r[0], r[1], r[2], r[3], r[4], r[5], r[6]])
    
    return mysql_count, len(new_rows)

print("=== 从通达信同步最新数据 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

csv_dir = Path('instance/qlib_export')
csv_dir.mkdir(parents=True, exist_ok=True)

# 获取MySQL各表最新日期
conn = create_connection(settings)
cur = conn.cursor()

mysql_latest = {}
for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
    cur.execute(f"SELECT MAX(date) FROM {table} WHERE date <= '2026-12-31'")
    max_date = cur.fetchone()[0] or '2000-01-01'
    mysql_latest[table] = max_date
    print(f"  {table} 最新日期: {max_date}", flush=True)

cur.close()
conn.close()

# 扫描通达信文件
sh_day = day_dir / 'sh' / 'lday'
sz_day = day_dir / 'sz' / 'lday'
bj_day = day_dir / 'bj' / 'lday'

all_files = []
for market, day_path in [('sh', sh_day), ('sz', sz_day), ('bj', bj_day)]:
    if day_path.exists():
        files = list(day_path.glob(f'{market}*.day'))
        all_files.extend(files)

print(f"\n通达信股票数: {len(all_files)}", flush=True)

# 并行同步
print("\n开始同步...", flush=True)
total_mysql = 0
total_csv = 0
synced = 0

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = []
    for file_path in all_files:
        table = f"stock_history_{file_path.stem[:2]}"
        min_date = mysql_latest.get(table, '2000-01-01')
        futures.append(executor.submit(sync_stock, file_path, settings, csv_dir, min_date))
    
    for i, future in enumerate(as_completed(futures), 1):
        mysql_count, csv_count = future.result()
        total_mysql += mysql_count
        total_csv += csv_count
        synced += 1
        
        if i % 500 == 0:
            print(f"  进度: {i}/{len(all_files)}, MySQL: {total_mysql}, CSV: {total_csv}", flush=True)

print("\n=== 同步完成 ===", flush=True)
print(f"成功同步: {synced}只股票", flush=True)
print(f"MySQL新增: {total_mysql}行", flush=True)
print(f"CSV新增: {total_csv}行", flush=True)
print(f"耗时: {time.time() - start_time:.2f}秒", flush=True)