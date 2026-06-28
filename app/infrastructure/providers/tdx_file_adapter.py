from __future__ import annotations

"""TDX local file data source adapter - direct file access for maximum speed."""


from typing import Any

import pandas as pd

from ...domain.enums import MarketCode
from ...domain.ports.market_ports import HistoryPort
from ..tdx_local.lday_reader import read_lday_file
from ..tdx_local.paths import TdxLocalPaths, resolve_tdx_root


class TDXFileHistoryAdapter(HistoryPort):
    """Direct TDX .day file reader - fastest possible access."""

    def __init__(self, tdx_root_path: str | None = None):
        self._tdx_root = resolve_tdx_root(tdx_root_path)
        self._paths = TdxLocalPaths(self._tdx_root) if self._tdx_root else None
        self._cache: dict[str, pd.DataFrame] = {}

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Read directly from TDX .day files."""
        df = self._read_to_dataframe(symbol, market)
        if df is None or df.empty:
            return []

        df["date"] = pd.to_datetime(df["date"])
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        filtered = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

        return filtered.to_dict(orient="records")

    def _read_to_dataframe(self, symbol: str, market: MarketCode) -> pd.DataFrame | None:
        """Read TDX .day file to DataFrame with caching."""
        cache_key = f"{market.value}:{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._paths:
            return None

        code = symbol.lower()
        if ":" in code:
            code = code.split(":", 1)[1]
        if code.startswith(("sh", "sz", "bj")):
            market_str = code[:2]
            code = code[2:]
        elif code.startswith("6"):
            market_str = "sh"
        elif code.startswith(("0", "3")):
            market_str = "sz"
        elif code.startswith(("8", "4", "9")):
            market_str = "bj"
        else:
            market_str = "sz"

        file_path = self._paths.vipdoc / market_str / "lday" / f"{market_str}{code}.day"

        if not file_path.is_file():
            return None

        rows = read_lday_file(file_path)
        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])

        self._cache[cache_key] = df
        return df

    def preload_symbols(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> int:
        """Preload multiple symbols into cache."""
        loaded = 0
        for sym in symbols:
            if self._read_to_dataframe(sym, market) is not None:
                loaded += 1
        return loaded

    def get_symbols_list(self, market: MarketCode = MarketCode.CN) -> list[str]:
        """List all available symbols in TDX directory."""
        if not self._paths:
            return []

        market_str = "sh" if market == MarketCode.CN else "sz"
        lday_dir = self._paths.vipdoc / market_str / "lday"

        if not lday_dir.is_dir():
            return []

        symbols = []
        for f in lday_dir.iterdir():
            if f.suffix == ".day":
                symbols.append(f.stem)

        return symbols

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached symbols."""
        return len(self._cache)


class TDXFileHistoryWithOptimization(TDXFileHistoryAdapter):
    """TDX reader with Arrow optimization for even better performance."""

    def __init__(self, tdx_root_path: str | None = None, use_arrow: bool = True):
        super().__init__(tdx_root_path)
        self._use_arrow = use_arrow
        self._arrow_cache: dict[str, Any] = {}

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Read with Arrow optimization if available."""
        if self._use_arrow:
            return self._read_with_arrow(symbol, market, start, end)

        return super().get_stock_history(symbol, market, start, end)

    def _read_with_arrow(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Read using Arrow for maximum performance."""
        try:
            import pyarrow as pa

            cache_key = f"{market.value}:{symbol}"
            if cache_key in self._arrow_cache:
                table = self._arrow_cache[cache_key]
            else:
                df = self._read_to_dataframe(symbol, market)
                if df is None:
                    return []
                table = pa.Table.from_pandas(df)
                self._arrow_cache[cache_key] = table

            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)

            mask = (pa.compute.greater_equal(table["date"], pa.scalar(start_dt)) &
                    pa.compute.less_equal(table["date"], pa.scalar(end_dt)))

            filtered = table.filter(mask)
            return filtered.to_pandas().to_dict(orient="records")

        except ImportError:
            return super().get_stock_history(symbol, market, start, end)
