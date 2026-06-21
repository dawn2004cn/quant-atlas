"""ATR and annual return metric tests."""

from __future__ import annotations

import pandas as pd
import pytest

from app.core.risk_controls import compute_atr
from app.infrastructure.compute import native_compute as nc


def test_compute_atr_uses_wilder_smoothing_not_simple_mean():
    df = pd.DataFrame(
        {
            "High": [12.0, 13.0, 14.0, 13.5, 15.0, 14.0, 16.0, 15.5, 17.0, 16.0,
                     18.0, 17.5, 19.0, 18.0, 20.0, 19.5],
            "Low": [10.0, 11.0, 12.0, 11.5, 13.0, 12.0, 14.0, 13.5, 15.0, 14.0,
                    16.0, 15.5, 17.0, 16.0, 18.0, 17.5],
            "Close": [11.0, 12.0, 13.0, 12.5, 14.0, 13.0, 15.0, 14.5, 16.0, 15.0,
                      17.0, 16.5, 18.0, 17.0, 19.0, 18.5],
        }
    )
    tr = pd.concat(
        [
            (df["High"] - df["Low"]).abs(),
            (df["High"] - df["Close"].shift(1)).abs(),
            (df["Low"] - df["Close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    wilder = compute_atr(df, window=14).iloc[-1]
    simple = tr.rolling(14).mean().iloc[-1]
    assert wilder != pytest.approx(simple)
    assert wilder < simple


def test_calculate_annual_return_uses_trading_days(monkeypatch):
    monkeypatch.setattr(nc, "HAS_RUST", False)
    monkeypatch.setattr(
        "app.infrastructure.compute.native_compute.get_runtime_int",
        lambda key, default: 250,
    )
    out_250 = nc.calculate_annual_return(100.0, 110.0, 250.0)
    monkeypatch.setattr(
        "app.infrastructure.compute.native_compute.get_runtime_int",
        lambda key, default: 365,
    )
    out_365 = nc.calculate_annual_return(100.0, 110.0, 250.0)
    assert out_250 == pytest.approx(10.0)
    assert out_365 > out_250
