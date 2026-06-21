# -*- coding: utf-8 -*-
"""Run TDX dayk daily sync for recent data only"""
import sys
sys.path.insert(0, '.')

from app.config import BASE_DIR
from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

print("Starting TDX daily sync (recent data only)...")
svc = TdxDaykSyncService(base_dir=BASE_DIR)

# Run daily sync - this only syncs the most recent data
result = svc.daily_sync_from_tdx_dayk(trade_date=None, limit=None)

print("\n=== Daily Sync Result ===")
for k, v in result.items():
    print(f"  {k}: {v}")