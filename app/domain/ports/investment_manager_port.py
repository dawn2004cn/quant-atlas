from __future__ import annotations

"""Port for investment manager persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ManagerRow:
    manager_id: str
    strategy_id: str
    name: str
    bio: str
    cohort: str
    deployed_at: str | None
    active: int
    tagline: str = ""
    specialty: str = ""


class InvestmentManagerRepository(ABC):
    """Contract for investment manager profiles, NAV, trades and holdings."""

    @abstractmethod
    def get_manager(self, manager_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def list_managers(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def upsert_manager(self, row: ManagerRow) -> None:
        raise NotImplementedError

    @abstractmethod
    def activate_next_batch(self, *, batch_size: int = 10) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def upsert_nav(
        self,
        *,
        manager_id: str,
        nav_date: str,
        equity: float,
        cash: float,
        total_fee: float,
        total_tax: float,
        note: str = "",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_nav_series(self, manager_id: str, *, limit: int = 420) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def append_trade(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_trades(self, manager_id: str, *, limit: int = 400) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def latest_holdings_snap_date_before(self, manager_id: str, snap_date: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_position_state(
        self,
        *,
        manager_id: str,
        symbol: str,
        shares: int,
        avg_cost: float,
        entry_cost: float,
        high_px: float,
        entry_date: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def trade_stats_by_manager(self) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_holdings_snap(self, manager_id: str, snap_date: str) -> list[dict[str, Any]]:
        raise NotImplementedError
