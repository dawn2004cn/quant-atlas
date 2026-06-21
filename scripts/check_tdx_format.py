# -*- coding: utf-8 -*-
"""Check TDX data format for different dates"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from app.config import AppSettings
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root

settings = AppSettings.from_env()
tdx_root = resolve_tdx_root(settings.tdx_root_path)
paths = TdxLocalPaths(tdx_root)

cn_symbol = "sh000001"
p = paths.lday_file_by_market(market="sh", code6="000001")
rows = read_lday_file(p)

# Show last 15 rows to see the pattern
print("Last 15 rows of sh000001:")
for r in rows[-15:]:
    print(f"  {r['date']}: O={r['open']:.2f} H={r['high']:.2f} L={r['low']:.2f} C={r['close']:.2f}")