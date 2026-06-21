"""极简同步脚本"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("Step 1: 导入配置...", flush=True)
from app.config import get_settings
settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}", flush=True)

print("Step 2: 读取CSV列表...", flush=True)
csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
print(f"CSV文件数: {len(csv_files)}", flush=True)

print("Step 3: 测试pandas导入...", flush=True)
import pandas as pd
print("pandas OK", flush=True)

print("Step 4: 测试SQLAlchemy...", flush=True)
from sqlalchemy import create_engine
db_url = f"mysql+pymysql://{settings.mysql.user}:{settings.mysql.password}@{settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}"
engine = create_engine(db_url)
print("SQLAlchemy OK", flush=True)

print("Step 5: 测试单只股票同步...", flush=True)
csv_path = csv_files[0]
df = pd.read_csv(csv_path)
stock_code = csv_path.stem
table = f"stock_history_{stock_code.lower()[:2]}"
df.to_sql(name=table, con=engine, if_exists='append', index=False, chunksize=1000)
print(f"同步成功: {stock_code}", flush=True)

engine.dispose()
print("测试完成!", flush=True)
