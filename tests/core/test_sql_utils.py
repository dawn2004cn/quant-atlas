"""SQL identifier validation helpers."""

from __future__ import annotations

import pytest

from app.core.utils.sql_utils import quote_identifier, validate_identifier


def test_validate_identifier_accepts_safe_names() -> None:
    assert validate_identifier("ai_trading_records") is True
    assert validate_identifier("stock_history_sh") is True


def test_validate_identifier_rejects_injection() -> None:
    assert validate_identifier("foo; DROP TABLE users") is False
    assert validate_identifier("") is False
    assert validate_identifier("1bad") is False


def test_quote_identifier_wraps_valid_name() -> None:
    assert quote_identifier("ai_trading_records") == "`ai_trading_records`"


def test_quote_identifier_raises_on_unsafe() -> None:
    with pytest.raises(ValueError):
        quote_identifier("evil`; DELETE FROM users; --")


def test_sentinel_rejects_unknown_table() -> None:
    from app.config import AppSettings
    from app.infrastructure.monitoring.sentinel import DataFreshnessSentinel

    sentinel = DataFreshnessSentinel(AppSettings())
    assert sentinel.check_freshness("users; DROP TABLE stock_history_sh") is False
