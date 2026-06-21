from __future__ import annotations
"""Quote gateway protocol for external market quote sources."""


from typing import Protocol


class QuoteGateway(Protocol):
    """Minimal quote HTTP gateway contract."""

    def fetch_quotes_text(self, normalized_symbols: list[str], timeout: float) -> str:
        """Fetch raw quote payload text for normalized symbol list."""
