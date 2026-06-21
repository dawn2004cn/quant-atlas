"""Data router MySQL history via TdxDaykWritePort."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.data.services.data_router_service import MarketDataService, ReadWriteSplitDataService
from app.domain.enums import MarketCode


class _FakeDaykRepo:
    _ROWS = [
        {
            "stock_code": "sh600519",
            "date": "2026-01-01",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
            "volume": 100,
            "amount": 1000,
        },
        {
            "stock_code": "sh600519",
            "date": "2026-01-15",
            "open": 2,
            "high": 3,
            "low": 2,
            "close": 3,
            "volume": 200,
            "amount": 2000,
        },
    ]

    def fetch_history_rows(self, table: str, codes: list[str]) -> list[dict]:
        assert table == "stock_history_sh"
        assert codes == ["sh600519"]
        return list(self._ROWS)

    def fetch_history_rows_for_code(
        self,
        stock_code: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        assert stock_code == "sh600519"
        out = list(self._ROWS)
        if start_date:
            out = [r for r in out if str(r["date"]) >= start_date]
        if end_date:
            out = [r for r in out if str(r["date"]) <= end_date]
        return out


class _FakeSyncSession:
    def __init__(self) -> None:
        self.written: list[tuple[str, list[dict[str, Any]]]] = []
        self.committed = False
        self.closed = False

    def write_bars(self, stock_code: str, rows: list[dict[str, Any]]) -> int:
        self.written.append((stock_code, rows))
        return len(rows)

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


class _FakeDaykRepoWithSession(_FakeDaykRepo):
    def __init__(self) -> None:
        self.session = _FakeSyncSession()

    def open_sync_session(self) -> _FakeSyncSession:
        return self.session


class _EmptyTdxHistory:
    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        return []

    def preload_symbols(self, symbols: list[str], market: MarketCode) -> int:
        return 0


def test_query_mysql_history_filters_date_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.data.services.data_router_service.get_tdx_dayk_write_port",
        lambda: _FakeDaykRepo(),
    )
    svc = MarketDataService()
    rows = svc._query_mysql_history("600519", MarketCode.CN, "2026-01-10", "2026-01-20")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-15"
    assert rows[0]["close"] == 3.0


def test_query_mysql_history_without_port_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.data.services.data_router_service.get_tdx_dayk_write_port",
        lambda: None,
    )
    svc = MarketDataService()
    assert svc._query_mysql_history("600519", MarketCode.CN, "2026-01-01", "2026-01-31") == []


def test_persist_to_mysql_via_sync_session(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _FakeDaykRepoWithSession()
    monkeypatch.setattr(
        "app.modules.data.services.data_router_service.get_tdx_dayk_write_port",
        lambda: repo,
    )
    svc = MarketDataService()
    bars = [
        {
            "date": "2026-01-01",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
            "volume": 100,
            "amount": 1000,
        }
    ]
    assert svc.write_backtest_result("600519", bars) is True
    assert repo.session.committed is True
    assert repo.session.closed is True
    assert repo.session.written == [("600519", bars)]


def test_read_write_split_falls_back_to_mysql_when_tdx_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.data.services.data_router_service.get_tdx_dayk_write_port",
        lambda: _FakeDaykRepo(),
    )
    svc = ReadWriteSplitDataService()
    svc._read_service._tdx = _EmptyTdxHistory()
    rows = svc.read_history("600519", MarketCode.CN, "2026-01-10", "2026-01-20")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-15"


def test_get_realtime_quote_delegates_to_cn_service(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"code": "600519", "price": 1688.0, "volume": 1000}

    class _FakeCnQuoteService:
        def fetch_map(self, symbols: list[str], *, prefer_tdx: bool = True) -> dict[str, dict[str, Any]]:
            assert symbols == ["600519"]
            return {"600519": expected}

    monkeypatch.setattr(
        "app.modules.data.services.cn_realtime_quote_service.CnRealtimeQuoteService",
        _FakeCnQuoteService,
    )
    svc = MarketDataService()
    quote = svc.get_realtime_quote("600519", MarketCode.CN)
    assert quote == expected


def test_get_realtime_quote_non_cn_uses_market_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.domain.entities import StockQuote

    class _FakeProvider:
        def get_realtime_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN):
            assert symbols == ["AAPL"]
            assert market == MarketCode.US
            return [
                StockQuote(
                    code="AAPL",
                    name="Apple",
                    market=MarketCode.US,
                    price=200.0,
                    change_pct=1.5,
                    volume=1000,
                )
            ]

    monkeypatch.setattr(
        "app.modules.system.services.helpers.market_data_provider.get_market_data_provider",
        lambda: _FakeProvider(),
    )
    svc = MarketDataService()
    quote = svc.get_realtime_quote("AAPL", MarketCode.US)
    assert quote is not None
    assert quote["code"] == "AAPL"
    assert quote["price"] == 200.0


def test_get_realtime_quote_non_cn_without_provider_returns_none() -> None:
    svc = MarketDataService()
    assert svc.get_realtime_quote("AAPL", MarketCode.US) is None

