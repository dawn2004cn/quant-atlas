"""Hot sector storage service integration-style tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.modules.market_data.services.hot_sector_storage_service import HotSectorStorageService
from app.infrastructure.repositories.mysql.null_hot_sector_repository import NullHotSectorStorageRepository


def test_resolve_sectors_auto_falls_back_to_live_with_null_repo() -> None:
    settings = MagicMock()
    settings.use_mysql = True
    svc = HotSectorStorageService(
        settings=settings,
        repository=NullHotSectorStorageRepository(),
    )
    live_rows = [{"sector_code": "BK0001", "name": "测试板块", "change_pct": 1.2}]

    with patch(
        "app.modules.market_data.services.hot_sector_storage_service._load_live_sectors",
        return_value=(live_rows, []),
    ) as mock_live:
        result = svc.resolve_sectors(limit=10, kind="all", source="auto")

    assert result["source_mode"] == "live"
    assert result["count"] == 1
    assert result["sectors"] == live_rows
    mock_live.assert_called_once_with(limit=10, kind="all")


def test_resolve_sectors_mysql_mode_raises_when_null_repo_empty() -> None:
    settings = MagicMock()
    settings.use_mysql = True
    svc = HotSectorStorageService(
        settings=settings,
        repository=NullHotSectorStorageRepository(),
    )

    with patch(
        "app.modules.market_data.services.hot_sector_storage_service._load_live_sectors",
        return_value=([], []),
    ):
        result = svc.resolve_sectors(limit=10, kind="all", source="auto")

    assert result["source_mode"] == "live"
    assert result["count"] == 0
