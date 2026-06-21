"""Unit tests for SQL identifier validation."""
from __future__ import annotations

from app.core.sql_safety import safe_sql_identifier, safe_table_name


def test_safe_sql_identifier_accepts_valid_names():
    assert safe_sql_identifier("stock_history", "fallback") == "stock_history"
    assert safe_table_name("ohlcv_cn", "stock_history") == "ohlcv_cn"


def test_safe_sql_identifier_rejects_injection():
    assert safe_sql_identifier("stock; DROP TABLE users", "stock_history") == "stock_history"
    assert safe_sql_identifier("", "stock_history") == "stock_history"
