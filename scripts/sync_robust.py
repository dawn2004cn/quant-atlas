"""健壮版同步脚本 - 处理连接断开重连"""
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
        connect_timeout=30
    )

print("=== 开始同步任务 ===", flush=True)
start_time = time.time()

settings = get_settings()
print(f"MySQL配置: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}", flush=True)

# 获取CSV中的股票代码
print("\n1. 读取CSV文件列表...", flush=True)
csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
csv_codes = {f.stem.upper() for f in csv_files}
print(f"CSV股票数: {len(csv_codes)}", flush=True)

# 获取已同步到MySQL的股票代码
print("\n2. 连接MySQL获取已同步股票...", flush=True)
conn = create_connection(settings)
mysql_codes = set()
try:
    with conn.cursor() as cur:
        for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
            print(f"  查询表: {table}...", flush=True)
            try:
                cur.execute(f"SELECT DISTINCT stock_code FROM {table}")
                for row in cur.fetchall():
                    if row[0]:
                        mysql_codes.add(str(row[0]).upper())
            except Exception as e:
                print(f"    表 {table} 错误: {e}", flush=True)
finally:
    conn.close()

print(f"MySQL股票数: {len(mysql_codes)}", flush=True)

# 找出缺失的股票
missing = sorted(list(csv_codes - mysql_codes))
print(f"\n3. 缺失股票数: {len(missing)}", flush=True)
if not missing:
    print("OK 所有股票都已同步到MySQL", flush=True)
    sys.exit(0)

print(f"   前5只缺失股票: {missing[:5]}", flush=True)

print("\n4. 开始导入pandas...", flush=True)
import pandas as pd
print("   导入完成", flush=True)

print("\n5. 开始同步数据...", flush=True)
total = len(missing)
synced = 0
skipped = 0
failed = []
batch_size = 50
start_sync = time.time()
conn = None
cur = None

for i, stock_code in enumerate(missing, 1):
    csv_path = csv_dir / f"{stock_code.lower()}.csv"
    if not csv_path.exists():
        csv_path = csv_dir / f"{stock_code}.csv"
        if not csv_path.exists():
            skipped += 1
            continue
    
    try:
        # 检查连接是否有效
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
        conn.commit()
        
        synced += 1
        
        if i % batch_size == 0:
            elapsed = time.time() - start_sync
            speed = synced / elapsed if elapsed > 0 else 0
            print(f"   已同步: {synced}/{total} ({(i/total)*100:.1f}%), 速度: {speed:.1f} 只/秒", flush=True)
            
    except Exception as e:
        failed.append((stock_code, str(e)))
        if conn:
            try:
                conn.rollback()
            except:
                pass
        conn = None
        cur = None
        if len(failed) <= 3:
            print("   FAIL " + stock_code + ": " + str(e)[:50], flush=True)

if conn:
    conn.close()

print("\n=== 同步完成 ===", flush=True)
print(f"成功: {synced}, 跳过: {skipped}, 失败: {len(failed)}", flush=True)
print(f"总耗时: {time.time() - start_time:.2f} 秒", flush=True)
if failed:
    print("失败列表前3个:", failed[:3], flush=True)
