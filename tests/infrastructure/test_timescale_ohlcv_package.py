"""TimescaleDB OHLCV package upsert (raw + factors + qfq + hfq)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.repositories.postgres.postgres_timescale_bar_repository import (
    PostgresTimescaleBarRepository,
    TimescaleSyncSession,
    _batch_write_bars,
)


def test_batch_write_bars_uses_executemany() -> None:
    cur = MagicMock()
    bars = [
        {
            "date": "2026-01-02",
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.0,
            "volume": 100,
            "amount": 1000,
        },
    ]
    n = _batch_write_bars(
        cur, table="market_bars", symbol="sh600519", market="CN", bars=bars, source="t"
    )
    assert n == 1
    cur.executemany.assert_called_once()


def test_upsert_ohlcv_package_writes_four_targets() -> None:
    repo = PostgresTimescaleBarRepository(MagicMock())
    raw = [
        {
            "date": "2026-01-02",
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.0,
            "volume": 100,
            "amount": 1000,
        },
        {
            "date": "2026-01-03",
            "open": 11.0,
            "high": 12.0,
            "low": 10.0,
            "close": 11.0,
            "volume": 110,
            "amount": 1100,
        },
    ]
    factors = [
        {"date": "2026-01-02", "factor": 0.5},
        {"date": "2026-01-03", "factor": 1.0},
    ]

    session = MagicMock(spec=TimescaleSyncSession)
    session.write_ohlcv_package.return_value = {
        "raw": 2,
        "factors": 2,
        "qfq": 0,
        "hfq": 0,
    }

    with patch.object(repo, "open_sync_session", return_value=session):
        out = repo.upsert_ohlcv_package(
            symbol="sh600519",
            market="CN",
            raw_rows=raw,
            factors=factors,
        )

    assert out == {"raw": 2, "factors": 2, "qfq": 0, "hfq": 0}
    session.write_ohlcv_package.assert_called_once()
    session.commit.assert_called_once()
    session.close.assert_called_once()


def test_write_ohlcv_package_writes_legacy_tables(monkeypatch) -> None:
    monkeypatch.setenv("TIMESCALE_USE_ADJUSTED_MATVIEWS", "0")
    monkeypatch.setenv("TIMESCALE_STORE_ADJUSTED_BARS", "1")
    conn = MagicMock()
    session = TimescaleSyncSession(conn, postgres=MagicMock())
    raw = [{"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 1, "amount": 1}]
    with patch(
        "app.infrastructure.repositories.postgres.postgres_timescale_bar_repository._batch_write_bars",
        return_value=1,
    ) as mock_bars, patch(
        "app.infrastructure.repositories.postgres.postgres_timescale_bar_repository._batch_write_factors",
        return_value=1,
    ):
        out = session.write_ohlcv_package(
            symbol="sh600519",
            market="CN",
            raw_rows=raw,
            factors=[{"date": "2026-01-02", "factor": 1.0}],
        )
    assert out["qfq"] > 0 and out["hfq"] > 0
    assert mock_bars.call_count == 3
