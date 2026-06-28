from __future__ import annotations
"""CSV file history data provider."""


from pathlib import Path
from typing import Any

import pandas as pd

from ...domain.enums import MarketCode
from ...domain.ports.market_ports import HistoryPort
from ...core.logger import get_logger

logger = get_logger(__name__)


def _guess_market(symbol: str) -> MarketCode:
    if symbol.startswith("6"):
        return MarketCode.SH
    elif symbol.startswith(("000", "001", "002", "003")):
        return MarketCode.SZ
    elif symbol.startswith(("8", "4", "9")):
        return MarketCode.BJ
    return MarketCode.CN


class CsvHistoryProvider(HistoryPort):
    """CSV file based history data provider.

    Expected CSV format:
        date,open,high,low,close,volume
        2024-01-01,100.0,102.0,99.0,101.5,1000000

    Directory structure:
        root_dir/
            SH/
                600000.csv
                600519.csv
            SZ/
                000001.csv
                000002.csv
    """

    def __init__(self, root_dir: str, include_subdirs: bool = True):
        self._root_dir = Path(root_dir)
        self._include_subdirs = include_subdirs
        self._cache: dict[str, pd.DataFrame] = {}

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode | None = None,
        start: str = "1900-01-01",
        end: str = "2100-01-01",
    ) -> list[dict[str, Any]]:
        """Get historical data from CSV file.

        Args:
            symbol: Stock symbol (e.g., 600000, 000001)
            market: Market code (auto-detected if not provided)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            List of OHLCV records
        """
        if market is None:
            market = _guess_market(symbol)

        cache_key = f"{market.value}:{symbol}"
        if cache_key in self._cache:
            df = self._cache[cache_key]
        else:
            df = self._load_csv(symbol, market)
            if df is not None:
                self._cache[cache_key] = df
            else:
                return []

        if df is None or df.empty:
            return []

        df["date"] = pd.to_datetime(df["date"])
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        filtered = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

        return filtered.to_dict(orient="records")

    def _load_csv(self, symbol: str, market: MarketCode) -> pd.DataFrame | None:
        market_str = market.value.lower() if hasattr(market, "value") else market.lower()
        if market_str == "cn":
            market_str = "sh" if symbol.startswith("6") else "sz"

        possible_paths = []
        if self._include_subdirs:
            possible_paths.append(self._root_dir / market_str / f"{symbol}.csv")
            possible_paths.append(self._root_dir / market_str.upper() / f"{symbol}.csv")

        possible_paths.append(self._root_dir / f"{symbol}.csv")
        possible_paths.append(self._root_dir / f"{symbol}_{market_str}.csv")

        upper_symbol = symbol.upper()
        possible_paths.append(self._root_dir / f"SZ{upper_symbol}.csv")
        possible_paths.append(self._root_dir / f"SH{upper_symbol}.csv")

        for path in possible_paths:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    required_cols = {"date", "close"}
                    if required_cols.issubset(df.columns):
                        df = df.sort_values("date")
                        logger.debug(f"Loaded CSV from {path}")
                        return df
                    else:
                        logger.warning(f"CSV missing required columns: {path}")
                except Exception as e:
                    logger.warning(f"Failed to read CSV {path}: {e}")

        logger.debug(f"CSV not found for {symbol} in {self._root_dir}")
        return None

    def list_available(self) -> dict[str, list[str]]:
        """List all available symbols in CSV directory.

        Returns:
            Dict mapping market to list of symbols
        """
        result: dict[str, list[str]] = {}
        if not self._root_dir.exists():
            return result

        for item in self._root_dir.iterdir():
            if item.is_dir():
                market = item.name.lower()
                symbols = [f.stem for f in item.glob("*.csv") if f.is_file()]
                result[market] = symbols
            elif item.is_file() and item.suffix == ".csv":
                name = item.stem.upper()
                if name.startswith("SZ"):
                    if "sz" not in result:
                        result["sz"] = []
                    result["sz"].append(name[2:])
                elif name.startswith("SH"):
                    if "sh" not in result:
                        result["sh"] = []
                    result["sh"].append(name[2:])
                else:
                    if "sh" not in result:
                        result["sh"] = []
                    result["sh"].append(name)

        return result

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()


def create_csv_history_provider(
    csv_dir: str,
    include_subdirs: bool = True,
) -> CsvHistoryProvider:
    """Create CSV history provider."""
    return CsvHistoryProvider(csv_dir, include_subdirs)


def create_qlib_export_provider(base_dir: str | None = None) -> CsvHistoryProvider:
    """Create provider for qlib export CSV files.

    Args:
        base_dir: Base directory. Defaults to project_root/instance/qlib_export

    Returns:
        CsvHistoryProvider configured for qlib export format
    """
    import app
    app_dir = Path(app.__file__).parent.parent
    if base_dir is None:
        base_dir = app_dir / "instance" / "qlib_export"
    return CsvHistoryProvider(str(base_dir), include_subdirs=False)
