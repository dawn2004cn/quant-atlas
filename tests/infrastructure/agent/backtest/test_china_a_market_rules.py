"""A-share T+1 and fee defaults for backtest engines."""

from __future__ import annotations

from datetime import date

import pandas as pd

from backtest.engines.china_a import ChinaAEngine
from backtest.engines.cn_market_rules import a_share_t1_blocks_sell, cn_stamp_tax_rate_for_date
from backtest.engines.composite import CompositeEngine
from backtest.models import Position


def _bar(ts: str) -> pd.Series:
    return pd.Series({"close": 100.0, "open": 100.0}, name=pd.Timestamp(ts))


def test_china_a_t1_blocks_sell_on_entry_bar():
    engine = ChinaAEngine({})
    engine._bar_idx = 3
    engine.positions["600519.SH"] = Position(
        symbol="600519.SH",
        direction=1,
        entry_price=100.0,
        entry_time=pd.Timestamp("2024-03-01"),
        size=100,
        entry_bar_idx=3,
    )
    assert engine.can_execute("600519.SH", 0, _bar("2024-03-01")) is False


def test_china_a_t1_allows_sell_on_next_trading_bar():
    engine = ChinaAEngine({})
    engine._bar_idx = 4
    engine.positions["600519.SH"] = Position(
        symbol="600519.SH",
        direction=1,
        entry_price=100.0,
        entry_time=pd.Timestamp("2024-03-01"),
        size=100,
        entry_bar_idx=3,
    )
    assert engine.can_execute("600519.SH", 0, _bar("2024-03-04")) is True


def test_china_a_fee_defaults_match_regulatory_rates():
    engine = ChinaAEngine({})
    assert engine.stamp_tax == 0.00025
    assert engine.transfer_fee == 0.00002
    sell_fee = engine.calc_commission(100, 10.0, 1, is_open=False)
    # commission min 5 + transfer 0.02 + stamp 0.25
    assert sell_fee == 5.0 + 0.02 + 0.25


def test_stamp_tax_rate_by_effective_date():
    assert cn_stamp_tax_rate_for_date(date(2020, 1, 1), 0.00025) == 0.001
    assert cn_stamp_tax_rate_for_date(date(2023, 9, 1), 0.00025) == 0.0005
    assert cn_stamp_tax_rate_for_date(date(2025, 1, 1), 0.00025) == 0.00025


def test_china_a_stamp_tax_uses_trade_date():
    engine = ChinaAEngine({})
    engine._trade_ts = pd.Timestamp("2020-06-01")
    sell_fee = engine.calc_commission(100, 10.0, 1, is_open=False)
    assert sell_fee == 5.0 + 0.02 + 1.0  # min comm + transfer + 0.1% stamp


def test_composite_a_share_t1_uses_entry_bar_idx():
    engine = CompositeEngine({"initial_cash": 1_000_000}, ["600519.SH"])
    engine._bar_idx = 2
    engine.positions["600519.SH"] = Position(
        symbol="600519.SH",
        direction=1,
        entry_price=100.0,
        entry_time=pd.Timestamp("2024-03-01"),
        size=100,
        entry_bar_idx=2,
    )
    assert a_share_t1_blocks_sell(engine, "600519.SH") is True
    engine._bar_idx = 3
    assert a_share_t1_blocks_sell(engine, "600519.SH") is False
