"""最终版同步脚本 - 带实时进度输出"""
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
if not missing:
    print("OK 所有股票都已同步到MySQL")
    sys.exit(0)

print(f"   前5只缺失股票: {missing[:5]}")

print("\n4. 开始导入pandas和SQLAlchemy...")
import pandas as pd
from sqlalchemy import create_engine
print("   导入完成")

# 创建SQLAlchemy引擎
db_url = f"mysql+pymysql://{settings.mysql.user}:{settings.mysql.password}@{settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}"
engine = create_engine(db_url, pool_size=10, max_overflow=20)

print("\n5. 开始同步数据...")
total = len(missing)
synced = 0
failed = []
batch_size = 50
start_sync = time.time()

for i, stock_code in enumerate(missing, 1):
    csv_path = csv_dir / f"{stock_code}.csv"
    if not csv_path.exists():
        continue
    
    try:
        df = pd.read_csv(csv_path)
        table = f"stock_history_{stock_code.lower()[:2]}"
        
        df.to_sql(
            name=table,
            con=engine,
            if_exists='append',
            index=False,
            chunksize=1000
        )
        synced += 1
        
        if i % batch_size == 0:
            elapsed = time.time() - start_sync
            speed = synced / elapsed if elapsed > 0 else 0
            print(f"   已同步: {synced}/{total} ({(i/total)*100:.1f}%), 速度: {speed:.1f} 只/秒")
            
    except Exception as e:
        failed.append((stock_code, str(e)))
        if len(failed) <= 3:
            print("   FAIL " + stock_code + ": " + str(e)[:50])

engine.dispose()

print("\n=== 同步完成 ===")
print(f"成功: {synced}, 失败: {len(failed)}")
print(f"总耗时: {time.time() - start_time:.2f} 秒")
if failed:
    print("失败列表前3个:", failed[:3])
