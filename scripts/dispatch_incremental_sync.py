# -*- coding: utf-8 -*-
"""Dispatch TDX incremental sync Celery task"""
import sys
sys.path.insert(0, '.')

from app.tasks.data_backfill_tasks import sync_incremental_tdx
from app.celery_app import celery_app

if __name__ == "__main__":
    if sync_incremental_tdx is None:
        print("Error: Celery is not configured")
        sys.exit(1)

    # Dispatch the task
    result = sync_incremental_tdx.delay()
    print(f"Task dispatched: {result.id}")
    print(f"Task state: {result.state}")

    # Wait for result (optional)
    try:
        import time
        for i in range(30):
            if result.ready():
                print(f"Result: {result.get()}")
                break
            time.sleep(2)
            print(f"Waiting... {i+1}/30")
        else:
            print("Task still running, check Celery logs")
    except Exception as e:
        print(f"Task error: {e}")