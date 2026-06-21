"""TimescaleDB dual-write on TDX day-K sync."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.modules.data.services.tdx_dayk_timescale_writer import persist_timescale_package


def test_persist_timescale_skipped_when_disabled() -> None:
    settings = SimpleNamespace(use_timescaledb=False)
    out = persist_timescale_package(
        settings,
        "sh600519",
        [{"date": "2026-01-01"}],
        [{"date": "2026-01-01", "factor": 1.0}],
    )
    assert out == {"raw": 0, "factors": 0, "qfq": 0, "hfq": 0}


def test_persist_timescale_calls_ohlcv_package(monkeypatch) -> None:
    settings = SimpleNamespace(use_timescaledb=True)
    port = MagicMock()
    port.upsert_ohlcv_package.return_value = {
        "raw": 3,
        "factors": 3,
        "qfq": 3,
        "hfq": 3,
    }
    rows = [
        {
            "date": "2026-01-01",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
            "volume": 1,
            "amount": 1,
        }
    ]
    factors = [{"date": "2026-01-01", "factor": 1.0}]

    monkeypatch.setattr(
        "app.modules.system.services.helpers.timescale_bar_access.get_timescale_bar_port",
        lambda: port,
    )

    out = persist_timescale_package(settings, "sh600519", rows, factors)
    assert out["raw"] == 3
    port.upsert_ohlcv_package.assert_called_once()


def test_persist_timescale_uses_thread_session(monkeypatch) -> None:
    settings = SimpleNamespace(use_timescaledb=True)
    ts_session = MagicMock()
    ts_session.write_ohlcv_package.return_value = {
        "raw": 2,
        "factors": 2,
        "qfq": 2,
        "hfq": 2,
    }
    rows = [
        {
            "date": "2026-01-01",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
            "volume": 1,
            "amount": 1,
        }
    ]
    factors = [{"date": "2026-01-01", "factor": 1.0}]

    monkeypatch.setattr(
        "app.modules.system.services.helpers.timescale_bar_access.get_timescale_bar_port",
        lambda: MagicMock(),
    )

    out = persist_timescale_package(
        settings, "sh600519", rows, factors, ts_session=ts_session
    )
    assert out["raw"] == 2
    ts_session.write_ohlcv_package.assert_called_once()
