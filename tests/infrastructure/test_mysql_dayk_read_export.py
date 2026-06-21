"""TDX day-K repository read helpers and incremental bin selection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch  # noqa: F401 — patch used in fallback test

import pytest

from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import MySQLTdxDaykRepository


def _cursor_context(cur: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm


def test_fetch_history_rows_for_code_builds_date_filter() -> None:
    repo = MySQLTdxDaykRepository(MagicMock())
    conn = MagicMock()
    cur = MagicMock()
    cur.description = [
        ("stock_code",),
        ("date",),
        ("open",),
        ("high",),
        ("low",),
        ("close",),
        ("volume",),
        ("amount",),
    ]
    cur.fetchall.return_value = [
        ("sh600519", "2026-01-15", 1, 2, 1, 2, 100, 1000),
    ]
    conn.cursor.return_value = _cursor_context(cur)
    repo._conn_port.connect = MagicMock(return_value=conn)

    rows = repo.fetch_history_rows_for_code(
        "sh600519",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-15"
    sql = cur.execute.call_args[0][0]
    assert "date >=" in sql
    assert "date <=" in sql


def test_list_stock_codes_updated_since_merges_tables() -> None:
    repo = MySQLTdxDaykRepository(MagicMock())
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.side_effect = [[("sh600519",)], [("sz000001",)], []]
    conn.cursor.return_value = _cursor_context(cur)
    repo._conn_port.connect = MagicMock(return_value=conn)

    codes = repo.list_stock_codes_updated_since("2026-05-01", limit=10)
    assert codes == ["sh600519", "sz000001"]
    assert cur.execute.call_count == 3


def test_list_stock_codes_updated_since_empty_date_falls_back() -> None:
    repo = MySQLTdxDaykRepository(MagicMock())
    with patch.object(
        repo,
        "list_history_stock_codes",
        return_value=["sh600519"],
    ) as mock_list:
        codes = repo.list_stock_codes_updated_since("", limit=5)
    mock_list.assert_called_once_with(limit=5)
    assert codes == ["sh600519"]
