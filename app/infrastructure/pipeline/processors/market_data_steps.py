"""Concrete pipeline processors."""

from app.infrastructure.pipeline.base import DataProcessor
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)

class MarketDataValidator(DataProcessor):
    """Step 1: Validate incoming market data."""
    def process(self, data: Any) -> Any:
        if not data.get("code"):
            logger.warning("Dropped invalid data: missing code.")
            return None
        return data

class DataNormalizer(DataProcessor):
    """Step 2: Normalize numeric types."""
    def process(self, data: Any) -> Any:
        # e.g., ensure price is float
        if "price" in data:
            data["price"] = float(data["price"])
        return data
