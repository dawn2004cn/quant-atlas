from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class DataScope(Enum):
    REALTIME = "realtime"
    HISTORICAL = "historical"
    BATCH = "batch"

@dataclass
class DataQuery:
    symbol: str
    market: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    interval: str = "1d"
    columns: list[str] | None = None
    scope: DataScope = DataScope.HISTORICAL

class UnifiedDataStore(ABC):
    """
    Abstract base class for the Unified Data Lake.
    All data access (SQLite, ClickHouse, QuestDB) must go through this interface
    to ensure the platform remains storage-agnostic.
    """

    @abstractmethod
    async def fetch_data(self, query: DataQuery) -> pd.DataFrame:
        """Fetch time-series data based on the query."""
        pass

    @abstractmethod
    async def write_data(self, symbol: str, data: pd.DataFrame, scope: DataScope):
        """Write data to the lake with specified scope."""
        pass

    @abstractmethod
    def get_health_status(self) -> dict[str, Any]:
        """Return storage health, latency, and capacity."""
        pass

class DataQualityFirewall:
    """
    The 'Firewall' ensures that data passing into the Strategy Engine
    is complete, aligned, and free of anomalies.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def validate(self, df: pd.DataFrame, query: DataQuery) -> tuple[pd.DataFrame, list[str]]:
        """
        Validates the dataframe against the query.
        Returns: (cleaned_df, list_of_warnings)
        """
        warnings = []
        if df.empty:
            warnings.append("Empty dataset returned.")
            return df, warnings

        # 1. Check for Missing Values (NaNs)
        nan_count = df.isna().sum().sum()
        if nan_count > 0:
            warnings.append(f"Detected {nan_count} missing values.")
            if self.strict_mode:
                df = df.dropna()
            else:
                df = df.ffill().bfill()

        # 2. Check for Time Alignment (Gap detection)
        if not df.empty and 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
            # Simplified gap detection: check if index is monotonic and consistent
            # In a real implementation, we would check against a calendar
            pass

        # 3. Outlier Detection (Z-Score based)
        # We only check numerical columns
        num_cols = df.select_dtypes(include=['number']).columns
        for col in num_cols:
            z_score = (df[col] - df[col].mean()) / df[col].std()
            outliers = (z_score.abs() > 5).sum()
            if outliers > 0:
                warnings.append(f"Column {col} contains {outliers} extreme outliers (Z > 5).")

        return df, warnings
