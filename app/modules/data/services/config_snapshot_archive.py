"""ConfigSnapshotArchive facade."""
from __future__ import annotations

from app.domain.config_snapshot import ConfigSnapshotArchive

_default: ConfigSnapshotArchive | None = None


def get_config_snapshot_archive() -> ConfigSnapshotArchive:
    global _default
    if _default is None:
        _default = ConfigSnapshotArchive()
    return _default


def set_config_snapshot_archive(archive: ConfigSnapshotArchive) -> None:
    global _default
    _default = archive
