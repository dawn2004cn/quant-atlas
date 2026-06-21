
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复CN:sh880005的CSV文件"""

from pathlib import Path
import sys
import pandas as pd

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService
    
    print("=" * 60)
    print("修复CN:sh880005的CSV")
    print("=" * 60)
    
    service = TdxDaykSyncService()
    
    cn_symbol = "sh880005"
    inst = service._get_qlib_instrument(cn_symbol)
    
    from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
    from app.infrastructure.tdx_local.lday_reader import read_lday_file
    from app.config import AppSettings
    
    settings = AppSettings.from_env()
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    paths = TdxLocalPaths(tdx_root)
    
    normalized_symbol = service._normalize_rows.__code__
    mkt = cn_symbol[:2]
    code6 = cn_symbol[-6:]
    p = paths.lday_file_by_market(market=mkt, code6=code6)
    rows = read_lday_file(p)
    
    norm_rows = service._normalize_rows(rows)
    n_csv, d0, d1 = service._write_csv(cn_symbol, norm_rows, merge=False)
    
    print(f"\nCSV已更新: {n_csv} 行")
    print(f"日期范围: {d0} 到 {d1}")
    
    print("\n完成！")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
