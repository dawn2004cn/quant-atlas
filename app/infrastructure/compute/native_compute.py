"""Bridge to Rust-native quant_core performance kernels.

Provides fast Sharpe ratio, max drawdown, and annualized return calculations
via the Rust ``quant_core`` PyO3 module, with numpy fallback.
"""
import logging

from app.core.runtime_config import get_runtime_int

logger = logging.getLogger(__name__)

try:
    import quant_core as _qc
    HAS_RUST = True
except ImportError:
    _qc = None
    HAS_RUST = False


def calculate_sharpe_ratio(portfolio_values: list[float]) -> float:
    """Annualized Sharpe ratio (risk-free=0) via Rust or numpy."""
    if HAS_RUST:
        return _qc.calculate_sharpe_ratio(portfolio_values)
    # numpy fallback
    import numpy as np
    if len(portfolio_values) < 2:
        return 0.0
    arr = np.array(portfolio_values, dtype=np.float64)
    returns = np.diff(arr) / arr[:-1]
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    if std == 0.0:
        return 0.0
    return mean / std * np.sqrt(252)


def calculate_max_drawdown(portfolio_values: list[float]) -> float:
    """Maximum drawdown as a positive percentage via Rust or numpy."""
    if HAS_RUST:
        return _qc.calculate_max_drawdown(portfolio_values)
    import numpy as np
    if not portfolio_values:
        return 0.0
    arr = np.array(portfolio_values, dtype=np.float64)
    peak = np.maximum.accumulate(arr)
    dd = (peak - arr) / peak * 100.0
    return float(np.max(dd))


def _trading_days_per_year() -> float:
    return float(get_runtime_int("BT_TRADING_DAYS_PER_YEAR", 250))


def calculate_annual_return(initial_capital: float, final_value: float, total_days: float) -> float:
    """Annualized return percentage via Rust or numpy (trading-day basis, default 250)."""
    if initial_capital <= 0.0 or total_days <= 0.0:
        return 0.0
    days_per_year = _trading_days_per_year()
    if HAS_RUST:
        return _qc.calculate_annual_return(initial_capital, final_value, total_days)
    return ((final_value / initial_capital) ** (days_per_year / total_days) - 1.0) * 100.0

def calculate_chip_distribution(
    prices: list[float],
    volumes: list[float],
    total_shares: float,
) -> dict[str, float]:
    """Chip distribution metrics via Rust (quant_core) or numpy fallback."""
    if HAS_RUST:
        result = _qc.calculate_chip_distribution(prices, volumes, total_shares)
        if result and len(result) >= 4:
            return {
                "profit_ratio": result[0],
                "avg_cost": result[1],
                "concentration_90": result[2],
                "concentration_70": result[3],
            }
    import numpy as np
    if not prices or not volumes or total_shares <= 0:
        return {"profit_ratio": 0.0, "avg_cost": 0.0, "concentration_90": 0.0, "concentration_70": 0.0}
    arr_p = np.array(prices, dtype=np.float64)
    arr_v = np.array(volumes, dtype=np.float64)
    n = min(len(arr_p), len(arr_v))
    total_v = float(np.sum(arr_v[:n]))
    if total_v <= 0:
        return {"profit_ratio": 0.0, "avg_cost": 0.0, "concentration_90": 0.0, "concentration_70": 0.0}
    avg_cost = float(np.average(arr_p[:n], weights=arr_v[:n]))
    current = float(arr_p[n - 1])
    profitable = float(np.sum(arr_v[:n][arr_p[:n] <= current]))
    profit_ratio = (profitable / total_v) * 100.0
    deviations = np.sort(np.abs(arr_p[:n] - avg_cost))
    c90 = float(deviations[int(n * 0.90) - 1] / max(avg_cost, 1.0) * 100.0) if n >= 10 else 0.0
    c70 = float(deviations[int(n * 0.70) - 1] / max(avg_cost, 1.0) * 100.0) if n >= 5 else 0.0
    return {"profit_ratio": profit_ratio, "avg_cost": avg_cost, "concentration_90": c90, "concentration_70": c70}
