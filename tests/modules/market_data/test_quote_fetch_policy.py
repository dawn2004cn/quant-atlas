"""Tests for quote fetch policy."""

from __future__ import annotations

import os

from app.modules.market_data.services.quote_fetch_policy import async_market_quotes_enabled


def test_async_market_quotes_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_ASYNC_MARKET_QUOTES", raising=False)
    assert async_market_quotes_enabled() is False


def test_async_market_quotes_enabled_values(monkeypatch):
    for value in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv("ENABLE_ASYNC_MARKET_QUOTES", value)
        assert async_market_quotes_enabled() is True
    monkeypatch.setenv("ENABLE_ASYNC_MARKET_QUOTES", "0")
    assert async_market_quotes_enabled() is False
