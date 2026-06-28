"""Optional VectorBT backend for parallel backtest comparison.

Does not replace FastBacktestEngine — only used when ``vectorbt`` is installed
(``pip install -r requirements-compute.txt``).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)


class VectorBTBacktestAdapter:
    """Thin wrapper around vectorbt buy-and-hold for A/B metrics."""

    def is_available(self) -> bool:
        try:
            import vectorbt

            return True
        except ImportError:
            return False

    def run_buy_hold(self, close: pd.Series, *, initial_capital: float = 100_000.0) -> dict[str, Any]:
        """Run vectorized buy-and-hold; raises if vectorbt is missing."""
        if not self.is_available():
            raise RuntimeError("vectorbt not installed; pip install -r requirements-compute.txt")

        import vectorbt as vbt

        close = close.dropna().astype(float)
        if close.empty:
            return {
                "backend": "vectorbt",
                "status": "empty",
                "metrics": {},
            }

        portfolio = vbt.Portfolio.from_holding(close, init_cash=initial_capital)
        total_return = float(portfolio.total_return())
        max_dd = float(portfolio.max_drawdown())
        sharpe = float(portfolio.sharpe_ratio()) if hasattr(portfolio, "sharpe_ratio") else 0.0

        return {
            "backend": "vectorbt",
            "status": "success",
            "metrics": {
                "expected_return": f"{total_return:.2%}",
                "max_drawdown": f"{abs(max_dd):.2%}",
                "sharpe_ratio": round(sharpe, 2) if not np.isnan(sharpe) else 0.0,
                "total_trades": 1,
            },
        }

    def compare_with_fast_preview(
        self,
        *,
        close: pd.Series,
        fast_metrics: dict[str, Any],
        initial_capital: float = 100_000.0,
    ) -> dict[str, Any]:
        """Return side-by-side metrics for wizard / API diagnostics."""
        if not self.is_available():
            return {
                "available": False,
                "reason": "vectorbt_not_installed",
                "fast": fast_metrics,
            }

        try:
            vbt_result = self.run_buy_hold(close, initial_capital=initial_capital)
        except Exception as exc:
            logger.warning("VectorBT compare failed: %s", exc)
            return {
                "available": True,
                "error": str(exc),
                "fast": fast_metrics,
            }

        return {
            "available": True,
            "fast": fast_metrics,
            "vectorbt": vbt_result.get("metrics", {}),
            "recommendation": "use_fast_engine_for_preview",
        }
