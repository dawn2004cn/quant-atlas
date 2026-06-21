
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""单独修复CN:sh880005的数据"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.config import AppSettings
    from app.infrastructure.database.mysql_client import ensure_mysql_schema, mysql_connect
    from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
    from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
    from app.infrastructure.tdx_local.lday_reader import read_lday_file
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService
    import csv
    
    print("=" * 60)
    print("修复CN:sh880005的数据")
    print("=" * 60)
    
    settings = AppSettings.from_env()
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    paths = TdxLocalPaths(tdx_root)
    
    # 读取通达信数据
    cn_symbol = SymbolNormalizer.normalize_cn_symbol("sh880005")
    mkt = cn_symbol[:2]
    code6 = cn_symbol[-6:]
    p = paths.lday_file_by_market(market=mkt, code6=code6)
    
    print(f"\n通达信文件: {p}")
    rows = read_lday_file(p)
    print(f"通达信数据行数: {len(rows)}")
    
    # 获取通达信数据到2026-04-23之后的数据
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService
    service = TdxDaykSyncService()
    norm_rows = service._normalize_rows(rows)
    
    target_date = "2026-04-23"
    filtered_rows = [r for r in norm_rows if r["date"] > target_date]
    
    print(f"\n需要同步的数据: {len(filtered_rows)} 行")
    for r in filtered_rows:
        print(f"  {r['date']}")
    
    # 连接MySQL并写入
    if settings.use_mysql and settings.mysql:
        print("\n连接MySQL...")
        conn = mysql_connect(settings.mysql)
        ensure_mysql_schema(conn)
        cur = conn.cursor()
        
        stock_code = SymbolNormalizer.to_db_code(cn_symbol, market="CN")
        print(f"股票代码: {stock_code}")
        
        # 先删除现有数据
        cur.execute("DELETE FROM stock_history_sh WHERE stock_code = %s AND date > %s", (stock_code, target_date))
        deleted = cur.rowcount
        print(f"已删除 {deleted} 行旧数据")
        
        # 写入新数据
        mysql_rows = 0
        for r in filtered_rows:
            cur.execute(
                """
                INSERT INTO stock_history_sh (stock_code, date, open, high, low, close, volume, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    volume = VALUES(volume),
                    amount = VALUES(amount)
                """,
                (stock_code, r["date"], r["open"], r["high"], r["low"], r["close"], r["volume"], r["amount"])
            )
            mysql_rows += cur.rowcount
        
        conn.commit()
        print(f"已写入 {mysql_rows} 行新数据")
        
        cur.close()
        conn.close()
    
    # 更新CSV
    print("\n更新CSV...")
    from app.application.services.qlib_pipeline_service import QlibPipelineService
    qlib = QlibPipelineService(base_dir=base_dir)
    
    inst = service._get_qlib_instrument(cn_symbol)
    out_dir = Path(qlib.export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{inst}.csv"
    
    # 读取现有CSV并合并
    import pandas as pd
    df_new = service._rows_to_df(filtered_rows)
    
    if csv_path.exists():
        df_old = pd.read_csv(csv_path, parse_dates=["date"])
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.assign(date=lambda x: pd.to_datetime(x["date"]))
        df = df.drop_duplicates(subset=["date"], keep="last")
        df = df.sort_values("date").reset_index(drop=True)
    else:
        df = df_new
    
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.to_csv(csv_path, index=False)
    print(f"CSV已更新: {csv_path}")
    
    print("\n" + "=" * 60)
    print("完成！")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
