# -*- coding: utf-8 -*-
from pathlib import Path
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
import sys

# Chinese path
tdx_path = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"

try:
    root_path = resolve_tdx_root(tdx_path)
    paths = TdxLocalPaths(root_path)
    print(f"TDX Root: {paths.root}")

    # Read a sample file (sh000001 - 上证指数)
    rows = read_lday_file(paths.lday_file(market_sh=True, code6='000001'))
    print(f'Total rows: {len(rows)}')

    if rows:
        print('First 3 rows:')
        for r in rows[:3]:
            print(f"  {r}")
        print('Last 3 rows:')
        for r in rows[-3:]:
            print(f"  {r}")

        # Check date range
        dates = [r.get('date') for r in rows if r.get('date')]
        print(f"\nDate range: {min(dates)} to {max(dates)}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()