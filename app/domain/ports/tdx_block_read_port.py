from __future__ import annotations

from typing import Any, Protocol


class TdxBlockReadPort(Protocol):
    """Read-only access to TDX block metadata and membership tables."""

    def load_membership_index(self, block_kind: str) -> dict[tuple[str, str], list[str]]:
        """Return {(kind, name): [symbol, ...]} for cache warm-up."""
        ...

    def list_blocks_meta(self, *, block_kind: str, limit: int) -> list[dict[str, Any]]:
        ...

    def load_members_bulk(
        self,
        block_keys: list[tuple[str, str]],
        *,
        per_block_limit: int,
    ) -> dict[tuple[str, str], list[dict[str, str]]]:
        ...

    def list_blocks_simple(self, *, block_kind: str | None = None) -> list[dict[str, Any]]:
        ...

    def list_symbol_blocks(self, symbols: list[str]) -> list[dict[str, Any]]:
        ...

    def list_watchlists(self) -> list[dict[str, Any]]:
        ...

    def list_watchlist_members(self, *, watchlist_name: str) -> list[dict[str, Any]]:
        ...

    def get_latest_finance_snapshot(self, symbol: str) -> dict[str, Any] | None:
        ...
