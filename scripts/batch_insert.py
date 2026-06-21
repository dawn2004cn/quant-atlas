# -*- coding: utf-8 -*-
"""Batch insert recent TDX data for multiple stocks"""
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer

settings = AppSettings.from_env()
tdx_root = resolve_tdx_root(settings.tdx_root_path)
paths = TdxLocalPaths(tdx_root)

conn = mysql_connect(settings.mysql)
cur = conn.cursor()

# 目标日期 (TDX 包含的日期)
target_dates = ["2026-04-23", "2026-04-24", "2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30"]

# 演示股票列表 (可以扩展到更多)
stock_list = [
    ("sh000001", "sh", "000001"),  # 上证指数
    ("sh000002", "sh", "000002"),  # 
    ("sz000001", "sz", "000001"),  # 平安银行
    ("sz000002", "sz", "000002"),  # 万科
    ("sh600000", "sh", "600000"),  # 浦发银行
    ("sh600519", "sh", "600519"),  # 贵州茅台
    ("sz300001", "sz", "300001"),  # 
    ("sh601318", "sh", "601318"),  # 中国平安
    ("sh601398", "sh", "601398"),  # 工商银行
]

total = 0
for cn_symbol, market, code6 in stock_list:
    p = paths.lday_file_by_market(market=market, code6=code6)
    if not p.exists():
        print(f"File not found: {p}")
        continue

    rows = read_lday_file(p)
    for target in target_dates:
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

            sql = """INSERT INTO stock_history (stock_code, date, open, high, low, close, volume, amount)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE open=VALUES(open), high=VALUES(high), low=VALUES(low),
                      close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)"""
            cur.execute(sql, (stock_code, date, open_p, high, low, close, volume, amount))
            total += 1

conn.commit()
print(f"\nTotal rows inserted/updated: {total}")
conn.close()