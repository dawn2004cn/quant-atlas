from __future__ import annotations

from datetime import date

import pandas as pd

from app.core.risk_controls import RiskControlParams
from app.infrastructure.providers.backtest_engine import BacktestEngine


def _limit_up_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": date(2024, 1, 2),
                "Open": 10.0,
                "High": 10.5,
                "Low": 9.8,
                "Close": 10.0,
                "Volume": 1_000_000,
            },
            {
                "Date": date(2024, 1, 3),
                "Open": 11.0,
                "High": 11.0,
                "Low": 10.9,
                "Close": 11.0,
                "Volume": 1_000_000,
            },
        ]
    ).set_index("Date")


def test_engine_blocks_cn_buy_at_limit_up():
    engine = BacktestEngine()
    risk = RiskControlParams(apply_cn_price_limits=True)
    df = _limit_up_df()
    assert not engine._cn_trade_allowed(risk, "sh600519", df, date(2024, 1, 3), "BUY")


def test_engine_allows_cn_buy_when_limits_disabled():
    engine = BacktestEngine()
    risk = RiskControlParams(apply_cn_price_limits=False)
    df = _limit_up_df()
    assert engine._cn_trade_allowed(risk, "sh600519", df, date(2024, 1, 3), "BUY")


def test_engine_skips_non_cn_symbol():
    engine = BacktestEngine()
    risk = RiskControlParams(apply_cn_price_limits=True)
    df = _limit_up_df()
    assert engine._cn_trade_allowed(risk, "AAPL", df, date(2024, 1, 3), "BUY")
