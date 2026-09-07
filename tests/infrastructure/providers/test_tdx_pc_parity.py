"""TDX PC parity: local vipdoc history + batched HQ quotes + TCP adapter."""

from __future__ import annotations

from datetime import date
from struct import pack
from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.infrastructure.providers.cn_tdx_provider import (
    TdxDataProvider,
    TdxHistoryProvider,
    TdxRealTimeProvider,
    tdx_rows_to_stock_quotes,
)
from app.infrastructure.providers.history_adapters import TdxFileAdapter, TdxTcpAdapter
from app.infrastructure.tdx_local.paths import resolve_tdx_root_configured


def _write_lday(root, market: str, code6: str, bars: list[tuple[int, int]]) -> None:
    folder = root / "vipdoc" / market / "lday"
    folder.mkdir(parents=True, exist_ok=True)
    body = b""
    for yyyymmdd, close_cents in bars:
        body += pack("IIIIIfII", yyyymmdd, close_cents, close_cents, close_cents, close_cents, 1.0, 100, 0)
    (folder / f"{market}{code6}.day").write_bytes(body)


def test_resolve_tdx_root_configured_uses_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: MagicMock(tdx_root_path=str(tmp_path)),
    )
    assert resolve_tdx_root_configured() == tmp_path.resolve()


def test_local_vipdoc_history_like_tdx_pc(tmp_path):
    _write_lday(tmp_path, "sh", "600519", [(20240102, 10000), (20240103, 10100)])
    hist = TdxHistoryProvider(tdx_root_path=str(tmp_path), use_qfq=False)
    rows = hist.get_stock_history("600519", MarketCode.CN, "2024-01-01", "2024-12-31")
    assert len(rows) == 2
    assert rows[0]["close"] == 100.0
    assert rows[1]["close"] == 101.0


def test_tdx_file_adapter_accepts_root_and_reads(tmp_path):
    _write_lday(tmp_path, "sz", "000001", [(20240102, 1100)])
    adapter = TdxFileAdapter(tdx_root=str(tmp_path))
    rows = adapter.get_history("000001", MarketCode.CN, date(2024, 1, 1), date(2024, 12, 31))
    assert len(rows) == 1
    assert rows[0]["close"] == 11.0


def test_get_history_falls_back_to_hq(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: MagicMock(tdx_root_path=str(tmp_path)))
    provider = TdxDataProvider(tdx_root_path=str(tmp_path), use_qfq=False)
    provider._realtime._tdx_mgr = MagicMock()
    provider._realtime._tdx_mgr.is_connected = True
    provider._realtime._tdx_mgr.execute.return_value = [
        {"year": 2024, "month": 1, "day": 3, "open": 10, "high": 11, "low": 9, "close": 10.5, "vol": 100, "amount": 1000},
    ]
    rows = provider.get_history("600519", MarketCode.CN, "2024-01-01", "2024-01-31")
    assert len(rows) == 1
    assert rows[0]["close"] == 10.5
    assert rows[0]["source"] == "tdx_hq"


def test_realtime_batches_security_quotes():
    rt = TdxRealTimeProvider()
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.execute.return_value = [
        {"code": "600519", "price": 1600.0, "last_close": 1580.0, "name": "茅台"},
        {"code": "000001", "price": 11.0, "last_close": 10.0, "name": "平安"},
    ]
    rt._tdx_mgr = mgr
    quotes = rt.get_quotes(["600519", "000001"])
    assert len(quotes) == 2
    mgr.execute.assert_called_once()
    args = mgr.execute.call_args.args
    assert args[0] == "get_security_quotes"
    assert len(args[1]) == 2
    assert quotes[0]["source"] == "tdx"
    assert quotes[0]["close"] == 1600.0


def test_tdx_rows_to_stock_quotes():
    quotes = tdx_rows_to_stock_quotes(
        [{"code": "600519", "price": 10.0, "last_close": 8.0, "name": "X", "vol": 1, "amount": 2, "open": 9, "high": 11, "low": 8}],
        MarketCode.CN,
    )
    assert len(quotes) == 1
    assert quotes[0].source == "tdx"
    assert quotes[0].code in {"600519", "sh600519"}
    assert quotes[0].change_pct > 0


def test_tcp_adapter_delegates_to_data_provider(monkeypatch):
    fake = MagicMock()
    fake.get_history.return_value = [{"date": "2024-01-02", "close": 1.0}]
    monkeypatch.setattr(
        "app.infrastructure.providers.cn_tdx_provider.create_tdx_provider",
        lambda **kwargs: fake,
    )
    rows = TdxTcpAdapter().get_history("600519", MarketCode.CN, date(2024, 1, 1), date(2024, 1, 31))
    assert rows[0]["close"] == 1.0
    fake.get_history.assert_called_once()
