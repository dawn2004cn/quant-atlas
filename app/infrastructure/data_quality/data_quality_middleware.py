"""Mandatory data quality firewall — enforced on all read paths.

Uses the existing DataQualityFirewall from unified_data_lake.py.
Wraps get_history() and similar methods to validate data before
it reaches strategy/backtest code.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Singleton firewall instance (lazy)
_firewall: Any = None


def get_firewall(strict_mode: bool = False):
    global _firewall
    if _firewall is None:
        from app.core.mesh.unified_data_lake import DataQualityFirewall
        _firewall = DataQualityFirewall(strict_mode=strict_mode)
    return _firewall


def enforce_data_quality(func: Callable) -> Callable:
    """Decorator: validate DataFrame output through DataQualityFirewall.

    Use on any method that returns market/factor data as a DataFrame.
    Warnings are logged; in strict mode, validation errors propagate.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            return result
        import pandas as pd
        if isinstance(result, pd.DataFrame):
            from app.core.mesh.unified_data_lake import DataQuery
            firewall = get_firewall(strict_mode=False)
            query = DataQuery(
                symbol=kwargs.get("symbol", kwargs.get("code", "unknown")),
                market=kwargs.get("market", "CN"),
            )
            cleaned, warnings = firewall.validate(result, query)
            for w in warnings:
                logger.warning("[DQ-Firewall] %s", w)
            return cleaned
        return result
    return wrapper


def check_dataframe_quality(
    df: Any,
    source: str = "unknown",
    strict: bool = False,
) -> list[str]:
    """Standalone quality check — returns warnings list.

    Usage:
        warnings = check_dataframe_quality(df, source="tdx_sync")
        if warnings:
            logger.warning("Data quality issues from %s: %s", source, warnings)
    """
    import pandas as pd
    if not isinstance(df, pd.DataFrame) or df.empty:
        return ["Empty dataset"]
    firewall = get_firewall(strict_mode=strict)
    from app.core.mesh.unified_data_lake import DataQuery
    query = DataQuery(symbol=source, market="CN")
    _, warnings = firewall.validate(df, query)
    return warnings
