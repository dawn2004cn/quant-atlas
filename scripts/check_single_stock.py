
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查单只股票CN:sh880005的数据情况"""

import os
import pymysql
from dotenv import load_dotenv
from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

load_dotenv()

mysql_host = os.getenv('MYSQL_HOST', 'localhost')
mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
mysql_user = os.getenv('MYSQL_USER', 'root')
mysql_password = os.getenv('MYSQL_PASSWORD', '')
mysql_db = os.getenv('MYSQL_DATABASE', 'quant_platform')

stock_code = "CN:sh880005"

print(f"Connecting to MySQL: {mysql_host}:{mysql_port}/{mysql_db}")
print(f"检查股票: {stock_code}")
print("=" * 60)

try:
    conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db,
        charset='utf8mb4'
    )
    
    cur = conn.cursor()
    
    # 查询MySQL中的数据
    print("\nMySQL中的数据:")
    cur.execute("SELECT date, open, high, low, close, volume, amount FROM stock_history_sh WHERE stock_code = %s ORDER BY date DESC LIMIT 20", (stock_code,))
    mysql_data = cur.fetchall()
    
    if mysql_data:
        for row in mysql_data:
            print(f"  {row[0]}: 开={row[1]}, 高={row[2]}, 低={row[3]}, 收={row[4]}, 量={row[5]}, 额={row[6]}")
        print(f"\nMySQL最新日期: {mysql_data[0][0]}")
    else:
        print("  无数据")
    
    # 检查通达信中的数据
    print("\n通达信中的数据:")
    try:
        from app.config import AppSettings
        from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
        from app.infrastructure.tdx_local.lday_reader import read_lday_file
        from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
        
        settings = AppSettings.from_env()
        tdx_root = resolve_tdx_root(settings.tdx_root_path)
        paths = TdxLocalPaths(tdx_root)
        
        cn_symbol = SymbolNormalizer.normalize_cn_symbol("sh880005")
        mkt = cn_symbol[:2]
        code6 = cn_symbol[-6:]
        p = paths.lday_file_by_market(market=mkt, code6=code6)
        print(f"通达信文件: {p}")
        print(f"文件存在: {p.exists()}")
        
        if p.exists():
            rows = read_lday_file(p)
            if rows:
                print(f"通达信数据行数: {len(rows)}")
                print(f"通达信最新日期: {rows[-1].get('date')}")
                
                print("\n通达信最近10条数据:")
                for row in rows[-10:]:
                    date_str = str(row.get('date', ''))[:10]
                    print(f"  {date_str}: 开={row.get('open')}, 高={row.get('high')}, 低={row.get('low')}, 收={row.get('close')}, 量={row.get('volume')}, 额={row.get('amount')}")
            else:
                print("  无数据")
    
    except Exception as e:
        print(f"检查通达信数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
