"""BacktestEngineAdapter — bridge between DefaultBacktestProvider and CompositeEngine.

DefaultBacktestProvider calls simulate_single_backtest(df, strategy, capital)
and simulate_portfolio_backtest(dfs, strategy, capital). CompositeEngine uses
run_backtest(config, loader, signal_engine, run_dir). This adapter translates
the legacy interface into the production engine.
"""

from __future__ import annotations

import warnings
from typing import Any

import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)


class BacktestEngineAdapter:
    """Wraps CompositeEngine with BacktestEngine's method signatures.

    Allows DefaultBacktestProvider to call CompositeEngine without changing
    the provider's interface. Marked as a bridge — will be removed once all
    callers migrate to BacktestEngineRegistry.get('production').
    """

    def __init__(self, config: dict | None = None) -> None:
        warnings.warn(
            "BacktestEngineAdapter is a temporary bridge. "
            "Use BacktestEngineRegistry.get('production') directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._config = config or {}
        self._engine = None

    def _lazy_engine(self, codes: list[str]):
        if self._engine is None:
            from app.infrastructure.agent.backtest.engines.composite import CompositeEngine
            self._engine = CompositeEngine(config=self._config, codes=codes)
        return self._engine

    def simulate_single_backtest(
        self, df: pd.DataFrame, strategy: Any, initial_capital: float,
    ) -> dict:
        """Single-symbol backtest via CompositeEngine.

        Converts the legacy df+strategy interface into CompositeEngine's
        run_backtest(config, loader, signal_engine, run_dir) interface.
        """
        warnings.warn("BacktestEngineAdapter.simulate_single_backtest is a bridge — use CompositeEngine directly", DeprecationWarning, stacklevel=2)

        engine = self._lazy_engine(codes=["000300.SH"])

        # Build a minimal config from what we have
        cfg = dict(self._config)
        cfg.setdefault("initial_capital", initial_capital)
        cfg.setdefault("start_date", str(df.index[0])[:10] if hasattr(df.index, "__getitem__") else "2000-01-01")
        cfg.setdefault("end_date", str(df.index[-1])[:10] if hasattr(df.index, "__getitem__") else "2099-12-31")

        # Build a minimal DataLoader from the DataFrame
        class _DfLoader:
            def __init__(self, dframe):
                self._dframe = dframe
            def fetch(self, codes, start, end, fields=None, interval="1D"):
                return {c: self._dframe for c in codes}

        class _SignalEngine:
            def __init__(self, dframe, strat):
                self._dframe = dframe
                self._strat = strat
            def generate(self, data_map):
                signals = {}
                for code, df in data_map.items():
                    sig_df = self._strat.generate_signals(df)
                    if sig_df is not None and isinstance(sig_df, pd.DataFrame) and "Signal" in sig_df.columns:
                        signals[code] = sig_df["Signal"]
                    else:
                        signals[code] = pd.Series(0, index=df.index)
                return signals

        import tempfile
        run_dir = tempfile.mkdtemp(prefix="bt_adapter_")

        result = engine.run_backtest(
            config=cfg,
            loader=_DfLoader(df),
            signal_engine=_SignalEngine(df, strategy),
            run_dir=run_dir,
        )

        # Flatten CompositeEngine result into BacktestEngine-compatible format
        metrics = {
            "final_value": result.get("final_value", initial_capital),
            "total_return": result.get("total_return", 0),
            "annual_return": result.get("annual_return", 0),
            "max_drawdown": result.get("max_drawdown", 0),
            "sharpe_ratio": result.get("sharpe", 0),
            "stock_data": {},
        }
        trades = result.get("trades", [])
        return {"metrics": metrics, "trades": trades}

    def simulate_portfolio_backtest(
        self, dfs: dict[str, pd.DataFrame], strategy: Any, initial_capital: float,
    ) -> dict:
        """Multi-symbol portfolio backtest via CompositeEngine."""
        warnings.warn("BacktestEngineAdapter.simulate_portfolio_backtest is a bridge — use CompositeEngine directly", DeprecationWarning, stacklevel=2)

        codes = list(dfs.keys())
        engine = self._lazy_engine(codes=codes)

        cfg = dict(self._config)
        cfg.setdefault("initial_capital", initial_capital)

        return engine.simulate_portfolio_backtest(dfs, strategy, initial_capital)
