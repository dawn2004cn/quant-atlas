# -*- coding: utf-8 -*-
"""Check TDX data for sh000001 (上证指数)"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root

tdx_path = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"
root_path = resolve_tdx_root(tdx_path)
paths = TdxLocalPaths(root_path)

# Read sh000001 (上证指数)
rows = read_lday_file(paths.lday_file(market_sh=True, code6='000001'))

print(f"Total rows: {len(rows)}")
print("\nLast 10 rows:")
for r in rows[-10:]:
    print(f"  {r['date']}: O={r['open']} H={r['high']} L={r['low']} C={r['close']} V={r['volume']}")