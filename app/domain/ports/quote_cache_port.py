from __future__ import annotations

"""Port for Redis-backed quote cache."""

from typing import Any, Protocol


class QuoteCachePort(Protocol):
    def get_quotes(self, codes: list[str]) -> dict[str, Any]:
        ...

    def set_quotes(self, quotes: dict[str, Any]) -> None:
        ...

    def clear_expired(self, max_age_seconds: int = 3600) -> int:
        ...
