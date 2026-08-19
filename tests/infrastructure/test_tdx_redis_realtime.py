"""Tests for TDX Redis quote session + live history merge (no heavy app bootstrap)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.domain.shared.cn_trading_session import is_cn_tdx_quote_session
from app.infrastructure.providers.tdx_live_history import merge_intraday_bar

_SH = ZoneInfo("Asia/Shanghai")


def test_session_morning_auction() -> None:
    dt = datetime(2026, 8, 19, 9, 20, tzinfo=_SH)
    assert is_cn_tdx_quote_session(dt) is True


def test_session_lunch_break() -> None:
    dt = datetime(2026, 8, 19, 12, 0, tzinfo=_SH)
    assert is_cn_tdx_quote_session(dt) is False


def test_session_afternoon() -> None:
    dt = datetime(2026, 8, 19, 14, 30, tzinfo=_SH)
    assert is_cn_tdx_quote_session(dt) is True


def test_session_after_close() -> None:
    dt = datetime(2026, 8, 19, 15, 5, tzinfo=_SH)
    assert is_cn_tdx_quote_session(dt) is False


def test_merge_updates_today_bar() -> None:
    bars = [
        {"date": "2026-08-18", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
        {"date": "2026-08-19", "open": 10.5, "high": 10.8, "low": 10.2, "close": 10.6, "volume": 500},
    ]
    quote = {
        "price": 10.9,
        "open_price": 10.5,
        "high_price": 11.0,
        "low_price": 10.2,
        "volume": 800,
        "amount": 9000,
        "source": "tdx",
    }
    with patch("app.infrastructure.providers.tdx_live_history.is_cn_tdx_quote_session", return_value=True):
        out = merge_intraday_bar(bars, quote, trade_date="2026-08-19")
    assert out[-1]["close"] == 10.9
    assert out[-1]["high"] >= 10.9
    assert out[-1]["volume"] >= 800


def test_merge_appends_today_when_missing() -> None:
    bars = [{"date": "2026-08-18", "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 10}]
    quote = {"price": 2.0, "open_price": 1.8, "high_price": 2.1, "low_price": 1.7, "volume": 5}
    with patch("app.infrastructure.providers.tdx_live_history.is_cn_tdx_quote_session", return_value=True):
        out = merge_intraday_bar(bars, quote, trade_date="2026-08-19")
    assert len(out) == 2
    assert out[-1]["date"] == "2026-08-19"
