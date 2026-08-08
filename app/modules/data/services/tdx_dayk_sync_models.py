from __future__ import annotations

"""Tdx 日 K 同步结果模型。"""

from dataclasses import dataclass
from typing import Literal

from app.core.runtime_config import get_runtime_bool

SyncStatus = Literal["ok", "skipped", "failed"]


def default_enable_timescale() -> bool:
    """历史入库默认写 Timescale（可用 TDX_SYNC_ENABLE_TIMESCALE=0 关闭）。"""
    return get_runtime_bool("TDX_SYNC_ENABLE_TIMESCALE", True)


def default_enable_mysql_history() -> bool:
    """历史入库默认不写 MySQL（可用 TDX_SYNC_ENABLE_MYSQL=1 临时打开）。"""
    return get_runtime_bool("TDX_SYNC_ENABLE_MYSQL", False)


@dataclass
class SyncResult:
    """单次同步结果."""

    stock_code: str
    status: SyncStatus = "skipped"
    mysql_rows: int = 0
    csv_rows: int = 0
    factor_rows: int = 0
    timescale_rows: int = 0
    timescale_factor_rows: int = 0
    timescale_qfq_rows: int = 0
    timescale_hfq_rows: int = 0
    min_date: str = ""
    max_date: str = ""
    error: str = ""

    @property
    def targets_written(self) -> bool:
        return self.mysql_rows > 0 or self.csv_rows > 0 or self.timescale_rows > 0

    @classmethod
    def skipped(cls, stock_code: str) -> SyncResult:
        return cls(stock_code=stock_code, status="skipped")

    @classmethod
    def failed(cls, stock_code: str, error: str = "") -> SyncResult:
        return cls(stock_code=stock_code, status="failed", error=error)
