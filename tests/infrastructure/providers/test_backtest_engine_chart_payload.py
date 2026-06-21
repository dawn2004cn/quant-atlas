"""BacktestEngine chart payload tests."""

from __future__ import annotations

import pandas as pd

from app.infrastructure.providers.backtest_engine import BacktestEngine, _ohlcv_series_payload


class _AlwaysBuy:
    name = "stub"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["Signal"] = 0
        if len(out) > 30:
            out.iloc[30, out.columns.get_loc("Signal")] = 1
        return out


def test_ohlcv_series_payload_shapes_dates_and_closes():
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Close": [10.0, 11.0],
        }
    )
    payload = _ohlcv_series_payload(df)
    assert payload["dates"] == ["2024-01-01", "2024-01-02"]
    assert payload["closes"] == [10.0, 11.0]


def test_simulate_single_backtest_returns_stock_data_and_equity_curve():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    rows = []
    price = 10.0
    for dt in dates:
        rows.append(
            {
                "Date": dt.strftime("%Y-%m-%d"),
                "Open": price,
                "High": price,
                "Low": price,
                "Close": price,
                "Volume": 1_000_000,
            }
        )
        price += 0.1
    df = pd.DataFrame(rows)
    engine = BacktestEngine()
    result = engine.simulate_single_backtest(df, _AlwaysBuy(), 100_000.0)
    assert result["stock_data"]["dates"]
    assert len(result["stock_data"]["closes"]) == 40
    assert len(result["equity_curve"]) == 40
    assert "sharpe_ratio" in result["metrics"]
