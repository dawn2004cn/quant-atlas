#!/usr/bin/env python3
"""Compatibility wrapper for the migrated investment-manager migration script."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "migrations" / "migrate_investment_managers_sqlite_to_mysql.py"),
        run_name="__main__",
    )
