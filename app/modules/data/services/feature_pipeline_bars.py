"""Load OHLCV bars for Feature Pipeline training (Timescale-first via multi-source)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_int

logger = get_logger(__name__)


def _bar_to_row(bar: dict[str, Any] | Any) -> dict[str, Any] | None:
    if bar is None:
        return None
    if not isinstance(bar, dict):
        bar = {
            "date": getattr(bar, "date", None) or getattr(bar, "trade_date", None),
            "close": getattr(bar, "close", None),
            "open": getattr(bar, "open", None),
            "high": getattr(bar, "high", None),
            "low": getattr(bar, "low", None),
            "volume": getattr(bar, "volume", None),
        }
    close = bar.get("close")
    if close is None:
        return None
    d = bar.get("date") or bar.get("trade_date") or bar.get("datetime")
    if d is None:
        return None
    if hasattr(d, "isoformat"):
        d = d.isoformat()
    return {
        "date": str(d)[:10],
        "close": float(close),
        "open": float(bar["open"]) if bar.get("open") is not None else None,
        "high": float(bar["high"]) if bar.get("high") is not None else None,
        "low": float(bar["low"]) if bar.get("low") is not None else None,
        "volume": float(bar["volume"]) if bar.get("volume") is not None else None,
    }


def load_cn_day_bars(
    *,
    symbol: str | None = None,
    lookback_days: int | None = None,
    min_bars: int = 60,
) -> dict[str, Any]:
    """Fetch CN daily bars for pipeline training.

    Returns ``{"ok", "bars", "symbol", "source", "synthetic": False}`` or ok=False.
    """
    sym = (symbol or get_runtime("FEATURE_PIPELINE_SYMBOL", "600519") or "600519").strip().upper()
    days = int(lookback_days if lookback_days is not None else get_runtime_int("FEATURE_PIPELINE_LOOKBACK_DAYS", 400))
    days = max(80, min(days, 3650))
    end = date.today()
    start = end - timedelta(days=days)
    try:
        from app.domain.enums import MarketCode
        from app.infrastructure.providers.history_adapters import get_multi_source_history_provider

        provider = get_multi_source_history_provider()
        raw = provider.get_history(sym, MarketCode.CN, start, end) or []
        rows: list[dict[str, Any]] = []
        for item in raw:
            row = _bar_to_row(item if isinstance(item, dict) else item)
            if row is not None:
                rows.append(row)
        source = getattr(provider, "last_source", None) or "multi_source"
        if len(rows) < min_bars:
            return {
                "ok": False,
                "bars": rows,
                "symbol": sym,
                "source": source,
                "error": f"insufficient_bars:{len(rows)}<{min_bars}",
                "synthetic": False,
            }
        return {
            "ok": True,
            "bars": rows,
            "symbol": sym,
            "source": source,
            "n_bars": len(rows),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "synthetic": False,
        }
    except Exception as exc:
        logger.warning("load_cn_day_bars failed symbol=%s: %s", sym, exc, exc_info=True)
        return {
            "ok": False,
            "bars": [],
            "symbol": sym,
            "source": None,
            "error": str(exc),
            "synthetic": False,
        }


def synthetic_day_bars(*, periods: int = 160) -> list[dict[str, Any]]:
    """Deterministic synthetic OHLCV for CI / empty-data fallback."""
    import pandas as pd

    dates = pd.date_range("2023-01-01", periods=max(80, periods), freq="B")
    close = 100.0
    rows: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        close = close * (1.0 + 0.001 * ((i % 7) - 3) + 0.0005 * ((i % 11) - 5))
        rows.append({"date": d.date().isoformat(), "close": float(close)})
    return rows
