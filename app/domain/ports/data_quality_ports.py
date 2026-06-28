from __future__ import annotations

"""Data quality monitoring ports."""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataQualityAlert:
    """Data quality alert."""
    severity: str
    symbol: str
    field: str
    expected: Any
    actual: Any
    message: str
    source: str


@dataclass(frozen=True)
class DataQualityReport:
    """Report of data quality checks."""
    total_checks: int
    passed: int
    failed: int
    alerts: list[DataQualityAlert] = field(default_factory=list)
    coverage: float = 0.0
    completeness: float = 0.0


@dataclass(frozen=True)
class SourceComparison:
    """Comparison result between data sources."""
    symbol: str
    field: str
    source_a: str
    source_b: str
    value_a: float | None = None
    value_b: float | None = None
    diff_pct: float | None = None
    anomaly: bool = False


class DataQualityPort(ABC):
    """Port for data quality monitoring."""

    @abstractmethod
    def check_completeness(self, symbol: str, market: str, days: int = 30) -> DataQualityReport:
        """Check data completeness (missing bars, gaps)."""
        raise NotImplementedError

    @abstractmethod
    def detect_anomalies(self, symbol: str, market: str) -> list[DataQualityAlert]:
        """Detect price/volume anomalies (e.g., >20% jump)."""
        raise NotImplementedError

    @abstractmethod
    def compare_sources(self, symbol: str, market: str) -> list[SourceComparison]:
        """Compare values across multiple sources (AkShare vs TDX vs Qlib)."""
        raise NotImplementedError

    @abstractmethod
    def check_adjustment_factors(self, symbol: str, market: str) -> list[DataQualityAlert]:
        """Check dividend/right-issue adjustment consistency."""
        raise NotImplementedError


class DataLineagePort(ABC):
    """Port for data lineage tracking."""

    @abstractmethod
    def record_fetch(self, symbol: str, source: str, timestamp: str, rows: int) -> str:
        """Record a data fetch event, return lineage_id."""
        raise NotImplementedError

    @abstractmethod
    def get_lineage(self, symbol: str, date: str) -> list[dict[str, Any]]:
        """Get all data sources used for a symbol on a specific date."""
        raise NotImplementedError
