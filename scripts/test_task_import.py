# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

try:
    from app.tasks.data_backfill_tasks import sync_incremental_tdx
    print(f"Task imported: {sync_incremental_tdx}")
    print(f"Task name: {sync_incremental_tdx.name}")
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()