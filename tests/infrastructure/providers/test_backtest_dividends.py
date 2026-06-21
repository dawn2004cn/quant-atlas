"""Cash dividend support in backtest engine."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.infrastructure.providers.backtest_dividends import (
    dividend_cash_for_bar,
    dividend_per_share,
)
from app.infrastructure.providers.backtest_engine import BacktestEngine


def test_dividend_per_share_reads_supported_columns():
    bar = pd.Series({"Close": 10.0, "cash_div": 0.25})
    assert dividend_per_share(bar) == 0.25


def test_dividend_per_share_ignores_zero_and_missing():
    assert dividend_per_share(pd.Series({"Close": 10.0})) == 0.0
    assert dividend_per_share(pd.Series({"Close": 10.0, "Dividend": 0.0})) == 0.0


def test_dividend_cash_for_bar_scales_by_shares():
    bar = pd.Series({"Dividend": 0.5})
    assert dividend_cash_for_bar(bar, 1000) == 500.0
    assert dividend_cash_for_bar(bar, 0) == 0.0


def test_apply_dividends_for_day_credits_cash_and_records_trade():
    engine = BacktestEngine()
    idx = [date(2024, 1, 1), date(2024, 1, 2)]
    df = pd.DataFrame(
        {"Close": [10.0, 10.0], "Dividend": [0.0, 0.3]},
        index=idx,
    )
    positions = {
        "2024-01-01": {"shares": 1000, "entry_price": 10.0, "current_price": 10.0},
    }
    trades: list[dict] = []
    cash = engine._apply_dividends_for_day(
        df,
        date(2024, 1, 2),
        positions,
        50_000.0,
        apply_dividends=True,
        trades=trades,
    )
    assert cash == pytest.approx(50_300.0)
    assert len(trades) == 1
    assert trades[0]["action"] == "dividend"
    assert trades[0]["amount"] == 300.0


def test_apply_dividends_for_day_skipped_when_disabled():
    engine = BacktestEngine()
    idx = [date(2024, 1, 2)]
    df = pd.DataFrame({"Close": [10.0], "Dividend": [0.5]}, index=idx)
    positions = {"x": {"shares": 100}}
    cash = engine._apply_dividends_for_day(
        df,
        date(2024, 1, 2),
        positions,
        1_000.0,
        apply_dividends=False,
    )
    assert cash == 1_000.0
