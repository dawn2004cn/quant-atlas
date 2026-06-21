# -*- coding: utf-8 -*-
"""Run TDX dayk full sync to MySQL + CSV + Qlib"""
import sys
sys.path.insert(0, '.')

from app.config import BASE_DIR
from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

print("Starting TDX full sync...")
svc = TdxDaykSyncService(base_dir=BASE_DIR)

# Run full sync (limit to first 10 for testing, remove limit for full sync)
result = svc.full_sync_from_tdx_dayk(limit=10)

print("\n=== Sync Result ===")
for k, v in result.items():
    print(f"  {k}: {v}")