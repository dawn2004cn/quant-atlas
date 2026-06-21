from __future__ import annotations

from typing import Any, Protocol


class HotSectorStoragePort(Protocol):
    """MySQL persistence for hot-sector snapshot tables."""

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
        """Insert snapshot header, sectors, members; update counts; prune old rows."""
        ...

    def list_snapshots(self, *, limit: int) -> list[dict[str, Any]]:
        ...

    def latest_snapshot_at(self) -> str | None:
        ...

    def list_sectors(
        self,
        *,
        snapshot_at: str,
        kind: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...

    def list_members(
        self,
        *,
        sector_code: str,
        snapshot_at: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...
