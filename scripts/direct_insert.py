# -*- coding: utf-8 -*-
"""Direct insert test for specific dates"""
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect, ensure_mysql_schema
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer

settings = AppSettings.from_env()
tdx_root = resolve_tdx_root(settings.tdx_root_path)
paths = TdxLocalPaths(tdx_root)

# Connect to MySQL
conn = mysql_connect(settings.mysql)
cur = conn.cursor()

# Test insert sh000001 for 2026-04-24
cn_symbol = "sh000001"
p = paths.lday_file_by_market(market="sh", code6="000001")
rows = read_lday_file(p)

# Find 2026-04-24
target = "2026-04-24"
bar = None
for r in rows:
    if str(r.get("date", ""))[:10] == target:
        bar = r
        break

if bar:
    stock_code = SymbolNormalizer.to_db_code(cn_symbol, market="CN")
    date = str(bar['date'])[:10]
    open_p = float(bar['open'])
    high = float(bar['high'])
    low = float(bar['low'])
    close = float(bar['close'])
    volume = float(bar['volume'])
    amount = float(bar['amount'])
    
    # Upsert
    sql = """INSERT INTO stock_history (stock_code, date, open, high, low, close, volume, amount)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
              ON DUPLICATE KEY UPDATE open=VALUES(open), high=VALUES(high), low=VALUES(low), 
              close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)"""
    cur.execute(sql, (stock_code, date, open_p, high, low, close, volume, amount))
    conn.commit()
    print(f"Inserted/Updated: {stock_code} {date} close={close}")
else:
    print(f"Date {target} not found in TDX")

conn.close()