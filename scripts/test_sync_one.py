# -*- coding: utf-8 -*-
"""Quick test: sync one stock for specific date"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from app.config import BASE_DIR, AppSettings
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
from app.infrastructure.database.mysql_client import mysql_connect, ensure_mysql_schema
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

settings = AppSettings.from_env()
tdx_root = resolve_tdx_root(settings.tdx_root_path)
paths = TdxLocalPaths(tdx_root)

# Test read sh000001 for 2026-04-24
cn_symbol = "sh000001"
p = paths.lday_file_by_market(market="sh", code6="000001")
print(f"Reading: {p}")
rows = read_lday_file(p)
print(f"Total rows: {len(rows)}")

# Find 2026-04-24
target = "2026-04-24"
for r in rows:
    if str(r.get("date", ""))[:10] == target:
        print(f"Found: {r}")
        break
else:
    print(f"Date {target} not found")
    # Show last few dates
    print("Last 5 dates:")
    for r in rows[-5:]:
        print(f"  {r['date']}")