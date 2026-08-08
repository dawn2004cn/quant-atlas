"""sync_one_stock unit tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.data.services.tdx_dayk_sync_runner import sync_one_stock


def test_sync_one_stock_skips_empty_rows(tmp_path: Path) -> None:
    settings = SimpleNamespace(use_timescaledb=False)
    result = sync_one_stock(
        cn_symbol="sh600519",
        raw_rows=[],
        mysql_session=None,
        csv_merge=False,
        settings=settings,
        export_dir=tmp_path,
    )
    assert result.status == "skipped"
    assert result.stock_code == "sh600519"


def test_sync_one_stock_csv_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(use_timescaledb=False)
    monkeypatch.setattr(
        "app.modules.data.services.tdx_dayk_sync_runner.calculate_adjustment_factors",
        lambda *_args, **_kwargs: [{"date": "2024-01-01", "factor": 1.0}],
    )
    rows = [
        {
            "date": "2024-01-01",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000,
            "amount": 10500,
        }
    ]
    result = sync_one_stock(
        cn_symbol="sh600519",
        raw_rows=rows,
        mysql_session=None,
        csv_merge=False,
        settings=settings,
        export_dir=tmp_path,
        enable_csv=True,
        enable_timescale=False,
    )
    assert result.status == "ok"
    assert result.csv_rows == 1
    assert (tmp_path / "SH600519.csv").exists()
