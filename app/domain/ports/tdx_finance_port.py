from __future__ import annotations
"""Port for TDX online finance snapshot fetching."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TdxFinanceSnapshot:
    symbol: str
    report_date: str
    total_shares: float
    float_shares: float
    eps: float
    bps: float
    net_profit: float
    revenue: float
    raw: dict[str, Any]


class TdxFinancePort(Protocol):
    def fetch_snapshot(self, symbol: str) -> TdxFinanceSnapshot | None:
        ...
