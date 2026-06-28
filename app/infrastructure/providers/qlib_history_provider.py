from __future__ import annotations

"""Qlib history data provider."""


from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...domain.enums import MarketCode
from ...domain.ports.market_ports import HistoryPort

logger = get_logger(__name__)


def _ensure_qlib_init(provider_uri: str | None = None) -> bool:
    """Ensure qlib is initialized."""
    try:
        import qlib
        if qlib.qlib_dir:
            return True
    except Exception as e:
        logger.warning("qlib_history_provider.py._ensure_qlib_init: %s", e)

    if not provider_uri:
        return False

    try:
        import qlib

        provider_uri = provider_uri.replace("\\", "/")
        if provider_uri.endswith(".csv"):
            provider_uri = provider_uri.replace(".csv", "")

        qlib.init(provider_uri=provider_uri, region="cn")
        return True
    except Exception as e:
        logger.warning(f"Failed to init qlib: {e}")
        return False


class QlibHistoryProvider(HistoryPort):
    """Qlib based history data provider.

    Requires qlib to be initialized with a data provider.
    """

    def __init__(
        self,
        provider_uri: str | None = None,
        symbol_prefix: str = "",
    ):
        self._provider_uri = provider_uri
        self._symbol_prefix = symbol_prefix
        self._initialized = False

    def _init_if_needed(self) -> bool:
        if self._initialized:
            return True
        self._initialized = _ensure_qlib_init(self._provider_uri)
        return self._initialized

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode | None = None,
        start: str = "1900-01-01",
        end: str = "2100-01-01",
    ) -> list[dict[str, Any]]:
        """Get historical data from qlib.

        Args:
            symbol: Stock symbol (e.g., 600000, 000001)
            market: Market code (not used, qlib uses symbol directly)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            List of OHLCV records
        """
        if not self._init_if_needed():
            logger.warning("qlib not initialized")
            return []

        try:
            from qlib.data import D

            sym = symbol.upper()
            if sym.startswith("SH") or sym.startswith("SZ") or sym.startswith("BJ"):
                qlib_symbol = self._symbol_prefix + sym
            elif sym.startswith("6"):
                qlib_symbol = self._symbol_prefix + f"SH{sym}"
            else:
                qlib_symbol = self._symbol_prefix + f"SZ{sym}"
            fields = "open,high,low,close,volume,$amount"

            df = D.features(
                [qlib_symbol],
                fields,
                start_date=start,
                end_date=end,
            )

            if df is None or df.empty:
                return []

            df = df.reset_index()
            col_names = ["symbol", "date", "open", "high", "low", "close", "volume"]
            if len(df.columns) >= 8:
                col_names.append("amount")
            df.columns = col_names[:len(df.columns)]

            df["date"] = pd.to_datetime(df["date"])

            df = df.sort_values("date")

            result = df.to_dict(orient="records")
            for r in result:
                r["symbol"] = symbol
                if pd.notna(r.get("volume")):
                    r["volume"] = int(r["volume"])
                if "amount" in r and pd.notna(r["amount"]):
                    r["amount"] = float(r["amount"])
                else:
                    r["amount"] = 0.0

            return result
        except Exception as e:
            logger.warning(f"qlib query failed for {symbol}: {e}")
            return []

    def set_provider_uri(self, uri: str) -> None:
        """Set the qlib provider URI."""
        self._provider_uri = uri
        self._initialized = False


def create_qlib_history_provider(
    provider_uri: str | None = None,
    symbol_prefix: str = "",
) -> QlibHistoryProvider:
    """Create qlib history provider.

    Args:
        provider_uri: qlib data provider URI (e.g., ~/.qlib/qlib_data/cn_data)
        symbol_prefix: Prefix to add to symbols (e.g., "SH." or "SZ.")
    """
    return QlibHistoryProvider(provider_uri, symbol_prefix)
