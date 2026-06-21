"""Tests for MarketService fresh quote fetch path."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.market_data.services.market_service import MarketApplicationService


@pytest.fixture
def market_svc():
    return MarketApplicationService(
        market_provider=SimpleNamespace(),
        industry_provider=SimpleNamespace(),
        stock_cache=None,
    )


def test_fetch_fresh_quotes_sync_by_default(market_svc, monkeypatch):
    monkeypatch.delenv("ENABLE_ASYNC_MARKET_QUOTES", raising=False)
    market_svc.get_quotes = MagicMock(return_value={"600519": {"code": "600519", "price": 1.0}})
    result = market_svc._fetch_fresh_quotes_dict(["600519"])
    assert result["600519"]["price"] == 1.0
    market_svc.get_quotes.assert_called_once_with(["600519"])


def test_fetch_fresh_quotes_async_when_enabled(market_svc, monkeypatch):
    monkeypatch.setenv("ENABLE_ASYNC_MARKET_QUOTES", "1")

    async def _async_quotes(codes):
        return {"000001": {"code": "000001", "price": 2.0}}

    market_svc.get_quotes_async = _async_quotes
    market_svc.get_quotes = MagicMock(return_value={})
    monkeypatch.setattr(
        "app.application.request_executor.run_async",
        lambda coro: asyncio.run(coro),
    )

    result = market_svc._fetch_fresh_quotes_dict(["000001"])
    assert result["000001"]["price"] == 2.0
    market_svc.get_quotes.assert_not_called()
