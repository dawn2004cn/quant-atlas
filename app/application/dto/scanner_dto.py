from __future__ import annotations

"""DTOs for Market Scanner services."""


from datetime import datetime

from pydantic import BaseModel


class ScannerStatusDTO(BaseModel):
    """Current status of the background scanner."""
    is_running: bool
    scan_count: int
    last_full_scan_at: datetime | None = None
    core_codes_count: int
    is_trading_time: bool


class ScanResultDTO(BaseModel):
    """Result of a single scan operation."""
    ok: bool
    skipped: bool = False
    reason: str | None = None
    batches: int = 0
    codes_count: int = 0
    scan_count: int = 0
    error: str | None = None


class ScannerSnapshotDTO(BaseModel):
    """Complete snapshot of scanner state."""
    status: ScannerStatusDTO
    result: ScanResultDTO | None = None
    timestamp: str
