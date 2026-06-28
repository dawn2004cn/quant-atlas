from __future__ import annotations

"""Market Data Plugin implementation."""


from app.core.plugins import QuantPlugin


class MarketDataPlugin(QuantPlugin):
    """Registers market data services."""

    name = "market_data"
    version = "1.0.0"
    priority = 50

    def register(self) -> None:
        """Placeholder — wire market providers via bootstrap_components."""
        return None
