"""超级安全同步脚本 - 使用CSV内置库和更宽松的解析"""
import sys
import gc
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql
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

print("=== 超级安全同步任务 ===", flush=True)
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

print("\n3. 开始同步（CSV模式）...", flush=True)
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
        # 使用Python内置CSV库读取，避免pandas的内存问题
        rows = []
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # 跳过标题行
            # 检查标题行是否包含 stock_code
            has_stock_code = header and 'stock_code' in ','.join(header).lower()
            for row in reader:
                if len(row) >= 7:  # 确保有足够的列
                    try:
                        # 根据是否有stock_code列调整索引
                        if has_stock_code:
                            # CSV格式: stock_code, date, open, high, low, close, volume, amount
                            rows.append((
                                stock_code.lower(),  # stock_code
                                row[1] if len(row) > 1 else '',  # date
                                float(row[2]) if row[2] else 0,  # open
                                float(row[3]) if row[3] else 0,  # high
                                float(row[4]) if row[4] else 0,  # low
                                float(row[5]) if row[5] else 0,  # close
                                float(row[6]) if row[6] else 0,  # volume
                                float(row[7]) if row[7] else 0,  # amount
                            ))
                        else:
                            # CSV格式: date, open, high, low, close, volume, amount
                            rows.append((
                                stock_code.lower(),  # stock_code
                                row[0] if len(row) > 0 else '',  # date
                                float(row[1]) if row[1] else 0,  # open
                                float(row[2]) if row[2] else 0,  # high
                                float(row[3]) if row[3] else 0,  # low
                                float(row[4]) if row[4] else 0,  # close
                                float(row[5]) if row[5] else 0,  # volume
                                float(row[6]) if row[6] else 0,  # amount
                            ))
                    except (ValueError, IndexError):
                        # 跳过无效行
                        pass

        if not rows:
            skipped += 1
            continue

        # 批量插入
        table = f"stock_history_{stock_code.lower()[:2]}"
        placeholders = ','.join(['%s'] * 8)
        sql = f"INSERT IGNORE INTO {table} (stock_code, date, open, high, low, close, volume, amount) VALUES ({placeholders})"

        cur.executemany(sql, rows)
        del rows
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
