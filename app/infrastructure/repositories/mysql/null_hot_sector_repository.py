from __future__ import annotations

from typing import Any

from app.domain.exceptions import ValidationError
from app.domain.ports.hot_sector_storage_port import HotSectorStoragePort


class NullHotSectorStorageRepository:
    """No-op hot-sector persistence when MySQL is disabled."""

    def save_ingest_batch(
        self,
        *,
        snapshot_at: str,
        trade_date: str,
        ingest_kind: str,
        snapshot_source: str,
        sector_params: list[tuple[Any, ...]],
        member_params: list[tuple[Any, ...]],
        retention_days: int,
    ) -> None:
        raise ValidationError("mysql_not_enabled")

    def list_snapshots(self, *, limit: int) -> list[dict[str, Any]]:
        return []

    def latest_snapshot_at(self) -> str | None:
        return None

    def list_sectors(
        self,
        *,
        snapshot_at: str,
        kind: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return []

    def list_members(
        self,
        *,
        sector_code: str,
        snapshot_at: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return []


def as_hot_sector_port(repo: HotSectorStoragePort | NullHotSectorStorageRepository) -> HotSectorStoragePort:
    return repo
