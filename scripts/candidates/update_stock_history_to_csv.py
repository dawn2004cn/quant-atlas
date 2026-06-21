#!/usr/bin/env python3
"""Compatibility wrapper for the candidate history-to-CSV update script."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "candidates" / "update_stock_history_to_csv.py"), run_name="__main__")

