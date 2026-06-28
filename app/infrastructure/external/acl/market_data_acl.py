from __future__ import annotations

"""Anti-Corruption Layer (ACL) for market data providers."""

from abc import ABC, abstractmethod
from typing import Any


class IMarketDataACL(ABC):
    """ACL interface to translate external market data into Domain DTOs."""

    @abstractmethod
    def fetch_standardized_data(self, *args, **kwargs) -> list[dict[str, Any]]:
        """Fetch and map to internal domain format."""
        raise NotImplementedError
