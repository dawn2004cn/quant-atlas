from __future__ import annotations

"""Google Finance data provider adapter.

Provides real-time US stock quotes via the googlefinance library.
Note: Google Finance API endpoint has been closed by Google, so this is provided as fallback.
"""

from typing import Any

from app.core.logger import get_logger
from app.domain.entities import StockQuote
from app.domain.enums import MarketCode

logger = get_logger(__name__)

_GOOGLE_FINANCE_COOLDOWN = 600  # 10 min
_google_finance_failures: int = 0
_google_finance_until: float = 0


def _is_google_finance_available() -> bool:
    """Check if googlefinance module is available and circuit is closed."""
    import time

    global _google_finance_failures, _google_finance_until

    if _google_finance_until > time.time():
        return False

    try:
        import googlefinance
        return True
    except ImportError:
        return False


def _get_google_finance_quotes(symbols: list[str]) -> list[StockQuote]:
    """Fetch real-time US stock quotes from Google Finance.

    Returns quotes for symbols like ['AAPL', 'MSFT'].
    Note: This API may not work reliably as Google has closed the endpoint.
    """
    import time
    from datetime import datetime

    global _google_finance_failures, _google_finance_until

    if not _is_google_finance_available():
        return []

    try:
        from googlefinance import getQuotes

        quotes = []
        for sym in symbols:
            try:
                raw_data = getQuotes(sym)
                if raw_data:
                    data = raw_data[0] if isinstance(raw_data, list) else raw_data
                    price = float(data.get("LastTradePrice", 0) or 0)
                    prev_close = float(data.get("PreviousClose", 0) or 0)
                    if prev_close == 0:
                        prev_close = price

                    quotes.append(StockQuote(
                        code=sym.upper(),
                        name=sym,
                        market=MarketCode.US,
                        price=price,
                        change_amount=price - prev_close,
                        change_pct=(price - prev_close) / prev_close * 100 if prev_close else 0,
                        volume=0,
                        source="googlefinance",
                        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
            except Exception as e:
                logger.debug(f"Google Finance fetch failed for {sym}: {e}")
                continue

        return quotes

    except Exception as e:
        _google_finance_failures += 1
        if _google_finance_failures >= 3:
            _google_finance_until = time.time() + _GOOGLE_FINANCE_COOLDOWN
            logger.info("Google Finance circuit opened, skipping %ss", _GOOGLE_FINANCE_COOLDOWN)
        logger.warning(f"Google Finance fetch failed: {e}")
        return []