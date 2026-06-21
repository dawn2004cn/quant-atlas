# -*- coding: utf-8 -*-
"""Run TDX dayk sync for specific date"""
import sys
sys.path.insert(0, '.')

from app.config import BASE_DIR
from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

# Sync specific dates that are missing
dates_to_sync = ["2026-04-23", "2026-04-24", "2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30"]

print("Starting TDX sync for specific dates...")
svc = TdxDaykSyncService(base_dir=BASE_DIR)

for target_date in dates_to_sync:
    print(f"\n=== Syncing {target_date} ===")
    result = svc.daily_sync_from_tdx_dayk(trade_date=target_date, limit=None)
    print(f"  codes_ok: {result.get('codes_ok', 0)}")
    print(f"  mysql_rows: {result.get('mysql_rows', 0)}")
    print(f"  csv_written: {result.get('csv_written', 0)}")

print("\n=== All done ===")