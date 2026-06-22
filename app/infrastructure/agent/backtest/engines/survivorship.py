"""
Survivorship-bias filter for backtest engines.

Filters out symbols that were not yet listed or already delisted
at the given backtest start date, using CNStockBasic metadata.
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)

# Status codes from CNStockBasic.listing_status
_STATUS_ACTIVE = {"L", "N"}  # L=Listed, N=New (first day)
_STATUS_SUSPENDED = {"S", "P"}  # S=Suspended, P=Pending


def filter_survivorship(
    codes: list[str],
    backtest_start: date,
    session=None,
) -> list[str]:
    """Remove symbols that did not exist or were delisted at backtest_start.

    Falls back gracefully if the database table is unavailable.
    """
    if not codes:
        return []

    try:
        from app.infrastructure.database.models.market import CNStockBasic
    except ImportError:
        logger.debug("CNStockBasic model not available ? skipping survivorship filter")
        return codes

    if session is None:
        try:
            from app.infrastructure.database.session import get_session
            session = get_session()
        except Exception:
            logger.debug("DB session unavailable ? skipping survivorship filter")
            return codes

    try:
        start_str = backtest_start.strftime("%Y%m%d")
        rows = (
            session.query(CNStockBasic.symbol, CNStockBasic.listing_date,
                          CNStockBasic.delist_date, CNStockBasic.listing_status)
            .filter(CNStockBasic.symbol.in_(codes))
            .all()
        )
    except Exception as exc:
        logger.warning("Survivorship filter DB query failed: %s ? skipping", exc)
        return codes
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    lookup = {r.symbol: r for r in rows}
    filtered: list[str] = []
    removed: list[str] = []

    for code in codes:
        row = lookup.get(code)
        if row is None:
            # Unknown symbol ? let it through (conservative)
            filtered.append(code)
            continue

        # Reject delisted symbols
        if row.delist_date and row.delist_date <= start_str:
            removed.append(code)
            continue

        # Reject symbols listed after backtest start
        if row.listing_date and row.listing_date > start_str:
            removed.append(code)
            continue

        # Reject suspended stocks (conservative: treat as untradeable)
        if row.listing_status and row.listing_status not in _STATUS_ACTIVE:
            removed.append(code)
            continue

        filtered.append(code)

    if removed:
        logger.info(
            "Survivorship filter removed %d/%d codes (delisted/not-yet-listed/suspended)",
            len(removed), len(codes),
        )

    return filtered
