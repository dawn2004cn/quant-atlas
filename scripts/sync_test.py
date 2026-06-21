"""测试同步脚本"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
import pymysql

settings = get_settings()

csv_dir = Path('instance/qlib_export')
csv_files = list(csv_dir.glob('*.csv'))
csv_codes = {f.stem for f in csv_files}
print(f"CSV股票数: {len(csv_codes)}")

conn = pymysql.connect(
    host=settings.mysql.host,
    port=settings.mysql.port,
    user=settings.mysql.user,
    password=settings.mysql.password,
    db=settings.mysql.database
)
mysql_codes = set()
try:
    with conn.cursor() as cur:
        for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
            try:
                cur.execute(f"SELECT DISTINCT stock_code FROM {table}")
                for row in cur.fetchall():
                    if row[0]:
                        mysql_codes.add(str(row[0]).upper())
            except Exception as e:
                print(f"表 {table} 错误: {e}")
finally:
    conn.close()

print(f"MySQL股票数: {len(mysql_codes)}")

missing = sorted(list(csv_codes - mysql_codes))
print(f"缺失股票数: {len(missing)}")
print(f"前5只缺失股票: {missing[:5]}")
