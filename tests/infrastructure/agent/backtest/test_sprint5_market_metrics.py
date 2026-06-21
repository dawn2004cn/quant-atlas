"""Tick slippage and risk-free rate resolution."""

from __future__ import annotations

import app.infrastructure.agent.backtest.risk_free_rate as risk_free_rate
from backtest.engines.cn_market_rules import cn_apply_tick_slippage, cn_price_tick_size


def test_cn_price_tick_size_main_board():
    assert cn_price_tick_size(10.0) == 0.01
    assert cn_price_tick_size(0.5) == 0.001


def test_cn_tick_slippage_floors_at_one_tick():
  # 10 * 0.001 = 0.01 == tick → buy at 10.01
    assert cn_apply_tick_slippage(10.0, 1, 0.001) == 10.01
    assert cn_apply_tick_slippage(10.0, -1, 0.001) == 9.99


def test_cn_tick_slippage_uses_proportional_when_larger_than_tick():
    assert cn_apply_tick_slippage(100.0, 1, 0.001) == 100.1


def test_resolve_risk_free_prefers_explicit_env(monkeypatch):
    monkeypatch.setenv("BT_RISK_FREE_SOURCE", "auto")
    monkeypatch.setenv("BT_RISK_FREE_ANNUAL", "0.03")
    risk_free_rate.fetch_cn_10y_bond_yield_annual.cache_clear()
    assert risk_free_rate.resolve_annual_risk_free_rate() == 0.03


def test_resolve_risk_free_uses_bond_when_auto(monkeypatch):
    monkeypatch.delenv("BT_RISK_FREE_ANNUAL", raising=False)
    monkeypatch.setenv("BT_RISK_FREE_SOURCE", "auto")
    risk_free_rate.fetch_cn_10y_bond_yield_annual.cache_clear()
    monkeypatch.setattr(
        risk_free_rate,
        "fetch_cn_10y_bond_yield_annual",
        lambda: 0.024,
    )
    assert risk_free_rate.resolve_annual_risk_free_rate() == 0.024
