"""TdxDaykSyncService unit tests — scan, normalize, SyncResult."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.data.services.tdx_dayk_sync_service import SyncResult, TdxDaykSyncService


def test_sync_result_skipped_and_failed_helpers():
    skipped = SyncResult.skipped("sh600519")
    assert skipped.status == "skipped"
    assert skipped.stock_code == "sh600519"
    assert skipped.targets_written is False

    failed = SyncResult.failed("sz000001", error="boom")
    assert failed.status == "failed"
    assert failed.error == "boom"


def test_sync_result_targets_written():
    row = SyncResult(stock_code="sh600519", status="ok", mysql_rows=10)
    assert row.targets_written is True
    empty = SyncResult(stock_code="sh600519", status="ok")
    assert empty.targets_written is False


def test_normalize_rows_dedupes_and_sorts():
    rows = [
        {"date": "2024-01-02", "close": 11.0, "volume": None},
        {"date": "2024-01-01", "close": 10.0, "amount": 100},
        {"date": "2024-01-02", "close": 12.0},
    ]
    normalized = TdxDaykSyncService._normalize_rows(rows)
    assert [r["date"] for r in normalized] == ["2024-01-01", "2024-01-02"]
    assert normalized[1]["close"] == 12.0
    assert normalized[0]["amount"] == 100


def test_scan_cn_codes_from_tdx_dayk(tmp_path: Path):
    root = tmp_path / "tdx"
    sh_lday = root / "vipdoc" / "sh" / "lday"
    sh_lday.mkdir(parents=True)
    (sh_lday / "sh600519.day").write_bytes(b"\x00")
    (sh_lday / "sh000001.day").write_bytes(b"\x00")

    codes = TdxDaykSyncService.scan_cn_codes_from_tdx_dayk(root)
    assert "sh600519" in codes
    assert "sh000001" in codes


def test_require_tdx_root_raises_when_unconfigured():
    settings = SimpleNamespace(tdx_root_path="")
    svc = TdxDaykSyncService(settings=settings, qlib_pipeline=MagicMock(), base_dir=Path("."))
    with pytest.raises(ValueError, match="TDX_ROOT_PATH"):
        svc._require_tdx_root()
