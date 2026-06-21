from app.domain.enums import MarketCode
from app.infrastructure.providers.market_data import (
    MultiSourceMarketProvider,
    _filter_sort_history,
    _finalize_history_bars,
    _sanitize_ohlc_bar,
)


class _UnavailableTdx:
    @property
    def is_available(self) -> bool:
        return False

    @property
    def is_connected(self) -> bool:
        return False

    def reconnect(self) -> None:
        return None

    def execute(self, method: str, *args):
        return None


def test_market_provider_returns_empty_history_without_tdx():
    provider = MultiSourceMarketProvider(tdx_factory=_UnavailableTdx)
    provider.get_realtime_quotes = lambda *args, **kwargs: []
    history = provider.get_stock_history("600519", market=MarketCode.CN, start="2024-01-01", end="2024-06-01")
    assert isinstance(history, list)


def test_filter_sort_history_orders_and_clips_window():
    rows = [
        {"date": "2024-03-01", "close": 3.0},
        {"date": "2024-01-15", "close": 1.0},
        {"date": "2024-02-01", "close": 2.0},
        {"date": "2023-12-31", "close": 0.0},
    ]
    out = _filter_sort_history(rows, "2024-01-01", "2024-02-15")
    assert [r["date"] for r in out] == ["2024-01-15", "2024-02-01"]


def test_sanitize_ohlc_bar_repairs_envelope():
    bar = _sanitize_ohlc_bar(
        {"date": "2024-01-02", "open": 10.0, "high": 9.0, "low": 11.0, "close": 10.5, "volume": 1000}
    )
    assert bar is not None
    assert bar["high"] == 10.5 and bar["low"] == 10.0


def test_finalize_dedupes_same_trade_date():
    rows = [
        {"date": "2024-01-02", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
        {"date": "2024-01-02", "open": 2, "high": 3, "low": 1.5, "close": 2.5},
    ]
    out = _finalize_history_bars(rows, MarketCode.CN)
    assert len(out) == 1
    assert out[0]["close"] == 2.5


def test_finalize_drops_cn_weekend_bar():
    """周末不应出现在 A 股日 K 序列中（数据源偶发脏日期时剔除）。"""
    rows = [
        {"date": "2024-01-05", "open": 1, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 100},
        {"date": "2024-01-06", "open": 1.1, "high": 1.3, "low": 1.0, "close": 1.2, "volume": 100},
        {"date": "2024-01-08", "open": 1.2, "high": 1.4, "low": 1.1, "close": 1.3, "volume": 100},
    ]
    out = _finalize_history_bars(rows, MarketCode.CN)
    dates = [r["date"] for r in out]
    assert "2024-01-06" not in dates
    assert "2024-01-05" in dates and "2024-01-08" in dates


def test_finalize_keeps_weekend_for_non_cn_market():
    rows = [
        {"date": "2024-01-06", "open": 1, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 100},
    ]
    out = _finalize_history_bars(rows, MarketCode.US)
    assert len(out) == 1
