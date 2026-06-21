# -*- coding: utf-8 -*-
"""Dispatch TDX incremental sync Celery task"""
import sys
sys.path.insert(0, '.')

from app.tasks.data_backfill_tasks import sync_incremental_tdx

if __name__ == "__main__":
    if sync_incremental_tdx is None:
        print("Error: Celery is not configured")
        sys.exit(1)

    print("Dispatching TDX incremental sync task...")

    # Dispatch the task asynchronously
    result = sync_incremental_tdx.delay()

    print(f"Task ID: {result.id}")
    print(f"Initial state: {result.state}")

    # Check if task is ready (non-blocking check)
    if result.ready():
        print(f"Result: {result.get()}")
    else:
        print("Task dispatched successfully. Check Celery worker for progress.")