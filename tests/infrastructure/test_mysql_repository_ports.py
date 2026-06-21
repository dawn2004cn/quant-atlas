"""MySQL repository / Null impl smoke tests (phases 13–16)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.errors import ValidationError
from app.infrastructure.repositories.deps import (
    create_hot_sector_repository,
    create_integration_probe_repository,
    create_tdx_base_data_repository,
    create_tdx_block_repository,
    create_tdx_dayk_repository,
)
from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import MySQLTdxDaykRepository
from app.infrastructure.repositories.mysql.null_hot_sector_repository import NullHotSectorStorageRepository


def _settings(*, use_mysql: bool = False) -> MagicMock:
    s = MagicMock()
    s.use_mysql = use_mysql
    s.mysql = MagicMock() if use_mysql else None
    return s


def test_null_hot_sector_reads_are_empty() -> None:
    repo = NullHotSectorStorageRepository()
    assert repo.list_snapshots(limit=5) == []
    assert repo.latest_snapshot_at() is None
    assert repo.list_sectors(snapshot_at="2026-01-01", kind="all", limit=10) == []
    assert repo.list_members(sector_code="BK0001", snapshot_at="2026-01-01", limit=10) == []


def test_null_hot_sector_save_raises_mysql_not_enabled() -> None:
    repo = NullHotSectorStorageRepository()
    with pytest.raises(ValidationError, match="mysql_not_enabled"):
        repo.save_ingest_batch(
            snapshot_at="2026-01-01 00:00:00",
            trade_date="2026-01-01",
            ingest_kind="all",
            snapshot_source="test",
            sector_params=[],
            member_params=[],
            retention_days=30,
        )


def test_create_hot_sector_repository_returns_null_without_mysql() -> None:
    repo = create_hot_sector_repository(_settings(use_mysql=False))
    assert isinstance(repo, NullHotSectorStorageRepository)


def test_create_tdx_repositories_none_without_mysql() -> None:
    settings = _settings(use_mysql=False)
    assert create_tdx_dayk_repository(settings) is None
    assert create_tdx_base_data_repository(settings) is None
    assert create_tdx_block_repository(settings) is None
    assert create_integration_probe_repository(settings) is None


def test_tdx_dayk_fetch_history_rejects_unknown_table() -> None:
    repo = MySQLTdxDaykRepository(MagicMock())
    assert repo.fetch_history_rows("not_a_history_table", ["sh600519"]) == []


def test_tdx_dayk_fetch_history_rejects_empty_codes() -> None:
    repo = MySQLTdxDaykRepository(MagicMock())
    assert repo.fetch_history_rows("stock_history_sh", []) == []
