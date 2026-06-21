
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试修复后的增量同步逻辑"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    print("=" * 60)
    print("测试修复后的增量同步逻辑")
    print("=" * 60)

    service = TdxDaykSyncService()

    # 测试单只股票的最新日期查询
    stock_code = "CN:sh880005"
    print(f"\n测试股票: {stock_code}")
    
    from app.infrastructure.database.mysql_client import mysql_connect
    
    conn = mysql_connect(service._settings.mysql)
    cur = conn.cursor()
    
    # 获取这只股票的最新日期
    latest_date = service._get_stock_latest_date(stock_code, cur)
    print(f"MySQL中最新日期: {latest_date}")
    
    # 读取通达信数据
    from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
    from app.infrastructure.tdx_local.lday_reader import read_lday_file
    
    tdx_root = resolve_tdx_root(service._settings.tdx_root_path)
    paths = TdxLocalPaths(tdx_root)
    
    from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
    cn_symbol = SymbolNormalizer.normalize_cn_symbol("sh880005")
    mkt = cn_symbol[:2]
    code6 = cn_symbol[-6:]
    p = paths.lday_file_by_market(market=mkt, code6=code6)
    rows = read_lday_file(p)
    
    # 过滤需要同步的数据
    norm_rows = service._normalize_rows(rows)
    filtered = [r for r in norm_rows if r["date"] > latest_date]
    
    print(f"\n需要同步的数据: {len(filtered)} 行")
    for r in filtered:
        print(f"  {r['date']}")
    
    cur.close()
    conn.close()
    
    print("\n测试完成！")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
