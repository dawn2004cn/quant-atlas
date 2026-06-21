from __future__ import annotations

"""Resolve annual risk-free rate for backtest Sharpe (decimal, e.g. 0.025 = 2.5%)."""

import logging
from functools import lru_cache
from typing import Optional

from app.core.runtime_config import get_runtime, get_runtime_float

logger = logging.getLogger(__name__)

_CN_10Y_LABELS = (
    "中债国债到期收益率:10年",
    "国债到期收益率:10年",
    "10年",
)


def _parse_yield_percent(value: object) -> Optional[float]:
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return None
    if pct <= 0 or pct > 30:
        return None
    return pct / 100.0


@lru_cache(maxsize=1)
def fetch_cn_10y_bond_yield_annual() -> Optional[float]:
    """Fetch latest China 10Y government bond yield as annual decimal."""
    try:
        import akshare as ak
    except ImportError:
        return None

    try:
        frame = ak.bond_china_yield()
    except Exception as exc:
        logger.warning("bond_china_yield failed: %s", exc, exc_info=True)
        return None

    if frame is None or frame.empty:
        return None

    name_col = next((c for c in frame.columns if "曲线" in str(c) or c in {"曲线名称", "name"}), None)
    yield_col = next(
        (c for c in frame.columns if "收益率" in str(c) or c in {"yield", "value"}),
        None,
    )
    if name_col is None or yield_col is None:
        return None

    subset = frame[frame[name_col].astype(str).str.contains("10年", na=False)]
    if subset.empty:
        for label in _CN_10Y_LABELS:
            hit = frame[frame[name_col].astype(str).str.contains(label, na=False)]
            if not hit.empty:
                subset = hit
                break
    if subset.empty:
        return None

    latest = subset.iloc[-1][yield_col]
    return _parse_yield_percent(latest)


def resolve_annual_risk_free_rate() -> float:
    """Annual risk-free rate for Sharpe excess return.

    Priority:
      1. ``BT_RISK_FREE_SOURCE=fixed`` → ``BT_RISK_FREE_ANNUAL``
      2. ``BT_RISK_FREE_SOURCE=none`` → 0
      3. ``auto`` (default): explicit ``BT_RISK_FREE_ANNUAL`` if set non-zero,
         else China 10Y bond yield via AkShare, else 0
    """
    source = get_runtime("BT_RISK_FREE_SOURCE", "auto").strip().lower()
    if source in {"none", "zero", "0"}:
        return 0.0
    if source == "fixed":
        return get_runtime_float("BT_RISK_FREE_ANNUAL", 0.0)

    explicit = get_runtime("BT_RISK_FREE_ANNUAL", "").strip()
    if explicit:
        return get_runtime_float("BT_RISK_FREE_ANNUAL", 0.0)

    if source in {"auto", "cn_bond_10y", "bond"}:
        fetched = fetch_cn_10y_bond_yield_annual()
        if fetched is not None:
            return fetched

    return 0.0
