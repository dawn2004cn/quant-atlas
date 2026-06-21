"""TDX day-K sync service factory and SyncResult semantics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.modules.data.services.tdx_dayk_sync_service import SyncResult, TdxDaykSyncService
from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service


def test_sync_result_status_helpers() -> None:
    skipped = SyncResult.skipped("sh600519")
    assert skipped.status == "skipped"
    failed = SyncResult.failed("sz000001", "boom")
    assert failed.status == "failed"
    assert failed.error == "boom"


def test_lday_tail_full_mode_reads_entire_file() -> None:
    assert TdxDaykSyncService._lday_tail_for_sync("full", "2026-01-01") is None


def test_lday_tail_incremental_with_latest() -> None:
    tail = TdxDaykSyncService._lday_tail_for_sync("incremental", "2026-01-01")
    assert tail is not None
    assert tail >= 30


def test_lday_tail_incremental_without_latest_reads_full() -> None:
    assert TdxDaykSyncService._lday_tail_for_sync("incremental", None) is None


@patch("app.infrastructure.repositories.common.deps.create_default_qlib_pipeline_service")
@patch("app.config.get_settings")
def test_create_tdx_dayk_sync_service_wires_dependencies(
    mock_get_settings: MagicMock,
    mock_qlib: MagicMock,
) -> None:
    mock_get_settings.return_value = MagicMock(use_mysql=False, tdx_root_path="/tdx")
    mock_qlib.return_value = MagicMock()
    svc = create_tdx_dayk_sync_service()
    assert isinstance(svc, TdxDaykSyncService)
    assert svc._settings is mock_get_settings.return_value
