#!/usr/bin/env python3
"""Inspect the legacy SQLite cache summary."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPO_ROOT / "scripts"
for _path in (str(_REPO_ROOT), str(_SCRIPTS_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from stock_cache_db import StockCache


if __name__ == "__main__":
    print("Checking legacy cache summary...")
    cache = StockCache()
    stats = cache.get_cache_stats()
    print(f"stock_count: {stats['stock_count']}")
    print(f"latest_update: {stats['latest_update']}")
    cache.close()
    print("Cache check complete")
