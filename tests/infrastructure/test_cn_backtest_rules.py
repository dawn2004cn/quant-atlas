from __future__ import annotations

import pandas as pd

from app.infrastructure.providers.cn_backtest_rules import (
    can_trade_cn_bar,
    can_trade_cn_on_date,
    cn_limit_threshold,
    is_cn_symbol,
)


def _daily_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df.set_index("Date")


def test_cn_limit_threshold_boards():
    assert cn_limit_threshold("600519") == 0.10
    assert cn_limit_threshold("300750") == 0.20
    assert cn_limit_threshold("688981") == 0.20
    assert cn_limit_threshold("830799") == 0.30


def test_is_cn_symbol():
    assert is_cn_symbol("sh600519")
    assert is_cn_symbol("600519")
    assert not is_cn_symbol("AAPL")


def test_limit_up_blocks_buy():
    df = _daily_frame(
        [
            {"Date": "2024-01-02", "Open": 10, "High": 10.5, "Low": 9.8, "Close": 10, "Volume": 1e6},
            {
                "Date": "2024-01-03",
                "Open": 11,
                "High": 11,
                "Low": 10.9,
                "Close": 11,
                "Volume": 1e6,
            },
        ]
    )
    ok, reason = can_trade_cn_on_date(df, df.index[1], side="BUY", limit_thr=0.10)
    assert not ok
    assert reason == "LIMIT_UP"


def test_limit_down_blocks_sell():
    df = _daily_frame(
        [
            {"Date": "2024-01-02", "Open": 10, "High": 10.2, "Low": 9.8, "Close": 10, "Volume": 1e6},
            {
                "Date": "2024-01-03",
                "Open": 9,
                "High": 9.1,
                "Low": 9,
                "Close": 9,
                "Volume": 1e6,
            },
        ]
    )
    ok, reason = can_trade_cn_on_date(df, df.index[1], side="SELL", limit_thr=0.10)
    assert not ok
    assert reason == "LIMIT_DOWN"


def test_one_word_board_blocks_trade():
    df = pd.DataFrame(
        [
            {"Open": 10, "High": 10.5, "Low": 9.8, "Close": 10, "Volume": 1e6},
            {"Open": 11, "High": 11, "Low": 11, "Close": 11, "Volume": 1e6},
        ]
    )
    ok, reason = can_trade_cn_bar(df, 1, side="BUY", limit_thr=0.10)
    assert not ok
    assert reason == "ONE_WORD_BOARD"
