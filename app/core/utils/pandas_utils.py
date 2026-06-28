from __future__ import annotations
"""Pandas and JSON data cleaning utilities."""


from datetime import datetime
from typing import Any
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def json_safe(v: Any) -> Any:
    """Ensure a value is JSON serializable, handling numpy/pandas types."""
    if isinstance(v, np.ndarray):
        return v.tolist()[:500] if len(v) <= 500 else v.tolist()
    if isinstance(v, pd.Series):
        return v.tolist()[:500] if len(v) <= 500 else v.tolist()
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            try:
                return v.tolist()[:500] if len(v) <= 500 else v.tolist()
            except Exception as exc:
                logger.warning("pandas_utils.serialize failed for type %s: %s", type(v).__name__, exc)
    if isinstance(v, (datetime, pd.Timestamp)):
        return str(v)[:32]
    if v is None:
        return v
    if isinstance(v, (int, float, str, bool)):
        return v
    try:
        if not isinstance(v, (np.ndarray, pd.Series, list, tuple)) and pd.isna(v):
            return None
    except Exception as e:
        logger.warning("pandas_utils.py.json_safe: %s", e)
    return str(v)[:500]


def safe_json_dump(data: Any) -> str:
    """Serialize data to JSON, handling numpy/pandas types."""
    import json

    def visitor(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        if isinstance(obj, (datetime, pd.Timestamp)):
            return str(obj)[:32]
        if hasattr(obj, "__dict__"):
            return str(obj)[:500]
        try:
            if pd.isna(obj):
                return None
        except Exception as e:
            logger.warning("pandas_utils.py.safe_json_dump: %s", e)
        return obj

    return json.dumps(data, default=visitor)


def safe_json_load(s: str) -> Any:
    """Parse JSON string, handling common errors."""
    import json

    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def safe_dataframe(data: Any) -> pd.DataFrame | None:
    """Convert various data to DataFrame, handling errors."""
    if data is None:
        return None
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, dict):
        try:
            return pd.DataFrame(data)
        except Exception:
            return None
    if isinstance(data, list):
        try:
            return pd.DataFrame(data)
        except Exception:
            return None
    return None


def can_trade_cn(df: pd.DataFrame, i: int, *, side: str, limit_thr: float) -> tuple[bool, str]:
    """Determine if a stock can be traded on a given day based on A-share rules (limit up/down)."""
    if i <= 0 or i >= len(df):
        return False, "index_out_of_range"
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    try:
        vol = float(row.get("Volume") or row.get("volume") or 0)
    except (TypeError, ValueError):
        vol = 0.0

    if not np.isfinite(vol) or vol <= 0:
        return False, "HALT_OR_NO_VOLUME"

    try:
        h = float(row.get("High") or row.get("high") or 0)
        l = float(row.get("Low") or row.get("low") or 0)
        c = float(row.get("Close") or row.get("close") or 0)
        pc = float(prev.get("Close") or prev.get("close") or 0)
    except (TypeError, ValueError):
        return False, "BAD_OHLC"

    if not (np.isfinite(h) and np.isfinite(l) and np.isfinite(c) and np.isfinite(pc)) or pc <= 0:
        return False, "BAD_OHLC"

    if abs(h - l) < 1e-12:
        return False, "ONE_WORD_BOARD"

    up = pc * (1.0 + float(limit_thr))
    dn = pc * (1.0 - float(limit_thr))
    eps = pc * 0.0005
    side_u = (side or "").strip().upper()

    if side_u == "BUY" and c >= (up - eps):
        return False, "LIMIT_UP"
    if side_u == "SELL" and c <= (dn + eps):
        return False, "LIMIT_DOWN"

    return True, "OK"
