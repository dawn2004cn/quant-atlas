from __future__ import annotations

import warnings
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.core.mesh.unified_data_lake import DataQuery, DataScope
from app.modules.data.services.data_lake_manager import DataLakeManager

logger = get_logger(__name__)

class FastBacktestEngine:
    """
    High-speed preview engine for quick strategy estimate.

    CRITICAL: This engine uses SIMPLIFIED logic and a 6-month window.
    ALWAYS validate final results via CompositeEngine (production).
    NEVER uses synthetic data — returns error status on empty lake.
    """

    def __init__(self, lake_manager: DataLakeManager) -> None:
        warnings.warn(
            "FastBacktestEngine is for preview only. "
            "Use CompositeEngine via BacktestEngineRegistry.get('production') for trading decisions.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.lake_manager = lake_manager

    async def run_preview(self, symbol: str, market: str, params: dict[str, Any], template_id: str) -> dict[str, Any]:
        """Runs a rapid simulation on the last 6 months of real data from the lake."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)

        query = DataQuery(
            symbol=symbol,
            market=market,
            start_date=start_date,
            end_date=end_date,
            scope=DataScope.HISTORICAL
        )

        try:
            df, warnings_list = await self.lake_manager.get_data(query)
            data_source = "lake"
            if df is None or df.empty:
                return {
                    "status": "insufficient_data",
                    "data_source": "none",
                    "is_synthetic": False,
                    "metrics": None,
                    "warnings": ["No historical data available for preview. Run a full backtest via CompositeEngine."],
                    "warning": "Preview unavailable — data lake empty for this symbol.",
                }
        except Exception as e:
            logger.warning("Lake fetch failed for %s: %s", symbol, e, exc_info=True)
            return {
                "status": "data_error",
                "data_source": "none",
                "is_synthetic": False,
                "metrics": None,
                "warnings": [f"Data fetch failed: {e}"],
                "warning": "Preview unavailable due to data error.",
            }

        returns = self._apply_strategy_logic(df, params, template_id)

        cumulative_return = (1 + returns).prod() - 1
        max_drawdown = self._calculate_max_drawdown(returns)
        portfolio_values = (1 + returns).cumprod().tolist()

        from app.infrastructure.compute.native_compute import calculate_sharpe_ratio
        sharpe = calculate_sharpe_ratio(portfolio_values) if len(portfolio_values) >= 2 else 0.0
        win_rate = (returns > 0).mean() if len(returns) > 0 else 0.0

        from app.core.metrics_helpers import record_backtest_completed
        record_backtest_completed(engine="fast_preview", outcome="success")

        return {
            "status": "success",
            "data_source": data_source,
            "is_synthetic": False,
            "metrics": {
                "expected_return": f"{cumulative_return:.2%}",
                "max_drawdown": f"{abs(max_drawdown):.2%}",
                "sharpe_ratio": round(sharpe, 2),
                "win_rate": f"{win_rate:.1%}",
                "total_trades": len(returns)
            },
            "warnings": warnings_list,
            "warning": "Preview based on recent 6M window. Final results require full backtest via CompositeEngine."
        }

    def _apply_strategy_logic(self, df: pd.DataFrame, params: dict[str, Any], template_id: str) -> pd.Series:
        """Apply a simplified version of the strategy logic to the data."""
        if 'close' not in df.columns:
            price_col = next((c for c in df.columns if 'close' in c.lower()), None)
            if price_col:
                df = df.rename(columns={price_col: 'close'})
            else:
                return pd.Series(0, index=df.index)

        returns = df['close'].pct_change().fillna(0)
        return returns

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        cum_returns = (1 + returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        return drawdown.min()

    def _generate_synthetic_data(self, start, end) -> pd.DataFrame:
        """Deprecated: preserved for backward compat only — raises RuntimeError."""
        raise RuntimeError(
            "Synthetic data generation has been removed. "
            "FastBacktestEngine requires real data from the data lake."
        )
