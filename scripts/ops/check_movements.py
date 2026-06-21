#!/usr/bin/env python3
"""Inspect a few rows from the legacy market movements cache."""

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
    cache = StockCache()
    movements = cache.get_market_movements(limit=5)
    print("movement_count:", len(movements))
    for index, movement in enumerate(movements, start=1):
        print(f"\nmovement {index}:")
        print("type:", type(movement))
        print("keys:", list(movement.keys()))
        for key, value in movement.items():
            print(f"{key}: {value}")
    cache.close()
