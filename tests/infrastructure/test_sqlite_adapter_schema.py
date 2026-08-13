"""SQLite adapter DDL must not use MySQL backtick quoting."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.infrastructure.database.adapters import SqliteAdapter


def test_sqlite_adapter_creates_history_tables(tmp_path: Path) -> None:
    db = tmp_path / "stock_cache.db"
    adapter = SqliteAdapter(str(db))
    conn = sqlite3.connect(db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "stocks" in tables
    for market in ("sh", "sz", "bj", "hk", "us", "btc"):
        assert f"stock_history_{market}" in tables
    # Keep adapter reference so GC does not close early in some envs.
    assert adapter.placeholder == "?"
