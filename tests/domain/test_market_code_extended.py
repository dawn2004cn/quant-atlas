"""Extended MarketCode coverage for FX / FUTURES backlog."""

from __future__ import annotations

from app.domain.enums import MARKET_BENCHMARKS, MARKET_CURRENCIES, MarketCode


def test_market_code_fx_futures_members() -> None:
    assert MarketCode.FX.value == "FX"
    assert MarketCode.FUTURES.value == "FUTURES"


def test_market_code_fx_futures_benchmark_currency() -> None:
    assert MarketCode.FX.benchmark == MARKET_BENCHMARKS[MarketCode.FX] == "USDCNY"
    assert MarketCode.FUTURES.benchmark == MARKET_BENCHMARKS[MarketCode.FUTURES] == "IF888"
    assert MarketCode.FX.currency == MARKET_CURRENCIES[MarketCode.FX] == "USD"
    assert MarketCode.FUTURES.currency == MARKET_CURRENCIES[MarketCode.FUTURES] == "CNY"
