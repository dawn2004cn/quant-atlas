#!/usr/bin/env python3
"""Compatibility wrapper for the candidate market-cache warmup script."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "candidates" / "warmup_market_cache.py"), run_name="__main__")

