from __future__ import annotations
"""Vectorized DTO for high-performance batch data processing.

This module implements the zero-copy DTO optimization from midify_plan8.md:
- StockQuotesBatchDTO: Vectorized storage for large market data
- Efficient numpy-based storage with lazy DTO conversion

Usage:
    batch_dto = StockQuotesBatchDTO.from_dict_list(quotes_list)
    single_quote = batch_dto[0]  # Lazy conversion to StockQuoteDTO
"""


from dataclasses import dataclass, field
from typing import Any, Iterator

import numpy as np


@dataclass
class StockQuotesBatchDTO:
    """Vectorized DTO for batch stock quotes.

    Uses numpy arrays internally for efficient storage.
    Only converts to individual DTOs when accessing specific elements.
    """
    symbols: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    names: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    prices: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    change_pcts: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    volumes: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))

    _count: int = 0
    _single_dto_class: Any = None

    def __post_init__(self):
        self._count = len(self.symbols)

    @classmethod
    def from_dict_list(cls, data: list[dict[str, Any]], single_dto_class: type | None = None) -> StockQuotesBatchDTO:
        """Create batch DTO from list of dictionaries."""
        if not data:
            return cls()

        return cls(
            symbols=np.array([d.get("code", d.get("symbol", "")) for d in data], dtype=object),
            names=np.array([d.get("name", "") for d in data], dtype=object),
            prices=np.array([float(d.get("price", 0) or 0) for d in data], dtype=np.float64),
            change_pcts=np.array([float(d.get("change_pct", 0) or 0) for d in data], dtype=np.float64),
            volumes=np.array([float(d.get("volume", 0) or 0) for d in data], dtype=np.float64),
            _single_dto_class=single_dto_class,
        )

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index: int) -> dict[str, Any]:
        """Get single item as dict (lazy conversion)."""
        if index >= self._count:
            raise IndexError("Index out of range")

        return {
            "code": self.symbols[index],
            "name": self.names[index],
            "price": float(self.prices[index]),
            "change_pct": float(self.change_pcts[index]),
            "volume": float(self.volumes[index]),
        }

    def filter(self, condition: np.ndarray) -> StockQuotesBatchDTO:
        """Filter batch by boolean condition."""
        return StockQuotesBatchDTO(
            symbols=self.symbols[condition],
            names=self.names[condition],
            prices=self.prices[condition],
            change_pcts=self.change_pcts[condition],
            volumes=self.volumes[condition],
            _single_dto_class=self._single_dto_class,
        )

    def top_n_by_volume(self, n: int) -> StockQuotesBatchDTO:
        """Get top N by volume."""
        if n >= self._count:
            return self
        indices = np.argsort(self.volumes)[-n:]
        return self.filter(np.isin(np.arange(self._count), indices))

    def top_n_by_change(self, n: int, ascending: bool = False) -> StockQuotesBatchDTO:
        """Get top N by change percentage."""
        if n >= self._count:
            return self
        indices = np.argsort(self.change_pcts)
        if not ascending:
            indices = indices[::-1]
        return self.filter(np.isin(np.arange(self._count), indices[:n]))

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of dicts."""
        return [self[i] for i in range(self._count)]

    @property
    def avg_price(self) -> float:
        """Average price."""
        return float(np.mean(self.prices)) if self._count > 0 else 0.0

    @property
    def total_volume(self) -> float:
        """Total volume."""
        return float(np.sum(self.volumes)) if self._count > 0 else 0.0

    @property
    def avg_change_pct(self) -> float:
        """Average change percentage."""
        return float(np.mean(self.change_pcts)) if self._count > 0 else 0.0


@dataclass
class MarketDataBatchDTO:
    """Vectorized DTO for batch market data."""
    timestamps: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    symbols: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    opens: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    highs: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    lows: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    closes: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    volumes: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))

    _count: int = 0

    def __post_init__(self):
        self._count = len(self.timestamps)

    @classmethod
    def from_ohlcv_list(cls, data: list[dict[str, Any]]) -> MarketDataBatchDTO:
        """Create from OHLCV data list."""
        if not data:
            return cls()

        return cls(
            timestamps=np.array([d.get("date", d.get("Date", "")) for d in data], dtype=object),
            symbols=np.array([d.get("symbol", d.get("code", "")) for d in data], dtype=object),
            opens=np.array([float(d.get("open", d.get("Open", 0)) or 0) for d in data], dtype=np.float64),
            highs=np.array([float(d.get("high", d.get("High", 0)) or 0) for d in data], dtype=np.float64),
            lows=np.array([float(d.get("low", d.get("Low", 0)) or 0) for d in data], dtype=np.float64),
            closes=np.array([float(d.get("close", d.get("Close", 0)) or 0) for d in data], dtype=np.float64),
            volumes=np.array([float(d.get("volume", d.get("Volume", 0)) or 0) for d in data], dtype=np.float64),
        )

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index: int) -> dict[str, Any]:
        """Get single OHLCV record."""
        return {
            "timestamp": self.timestamps[index],
            "symbol": self.symbols[index],
            "open": float(self.opens[index]),
            "high": float(self.highs[index]),
            "low": float(self.lows[index]),
            "close": float(self.closes[index]),
            "volume": float(self.volumes[index]),
        }

    def returns(self) -> np.ndarray:
        """Calculate returns as numpy array."""
        if self._count < 2:
            return np.array([], dtype=np.float64)
        return np.diff(self.closes) / self.closes[:-1]

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of dicts."""
        return [self[i] for i in range(self._count)]