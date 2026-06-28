from __future__ import annotations

"""High-performance computing module - moves Pandas calculations to Infrastructure layer.

This module implements the performance optimization from midify_plan7.md:
- Vectorized operations using numpy for matrix calculations
- Optional numba JIT compilation for hot paths
- Zero-copy transfer using DTO lists instead of full DataFrames

Following the principle: "Complex matrix operations in Infrastructure, not Application layer"
"""


from typing import Any

import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)

NUMBA_AVAILABLE = False
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    def jit(*args, **kwargs):
        """Dummy decorator when numba not available."""
        def decorator(func):
            return func
        return decorator


class VectorizedCalculator:
    """High-performance vectorized calculator using numpy.

    This class performs complex matrix operations in the Infrastructure layer,
    keeping the Application layer focused on business logic rather than
    low-level computations.
    """

    NUMBA_AVAILABLE = False
    _numba_core = None

    @classmethod
    def _init_numba(cls):
        if cls._numba_core is None:
            try:
                from numba import jit, prange
                cls._numba_core = type('NumbaCore', (), {'jit': jit, 'prange': prange})()
                cls.NUMBA_AVAILABLE = True
            except ImportError:
                cls._numba_core = type('NumbaCore', (), {'jit': lambda f: f, 'prange': range})()

    @staticmethod
    def calculate_returns(prices: list[float], period: int = 1) -> list[float]:
        """Calculate returns using vectorized numpy operations."""
        if not prices or len(prices) < period + 1:
            return []

        price_array = np.array(prices, dtype=np.float64)
        returns = np.diff(price_array) / price_array[:-1]

        if period > 1:
            returns = np.convolve(returns, np.ones(period) / period, mode='valid')

        return returns.tolist()

    @staticmethod
    def calculate_volatility(
        prices: list[float],
        window: int = 20,
        annualize: bool = True,
    ) -> float:
        """Calculate rolling volatility using vectorized operations."""
        if not prices or len(prices) < window:
            return 0.0

        returns = np.diff(np.log(np.array(prices, dtype=np.float64)))
        if len(returns) < window:
            return 0.0

        recent_returns = returns[-window:]
        volatility = np.std(recent_returns, ddof=1)

        if annualize:
            volatility *= np.sqrt(252)

        return float(volatility)

    @staticmethod
    def calculate_sharpe_ratio(
        returns: list[float],
        risk_free_rate: float = 0.03,
    ) -> float:
        """Calculate Sharpe ratio using vectorized operations."""
        if not returns or len(returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=np.float64)
        excess_returns = returns_array - (risk_free_rate / 252)

        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns, ddof=1)

        if std_return == 0:
            return 0.0

        return float(mean_return / std_return * np.sqrt(252))

    @staticmethod
    def calculate_max_drawdown(prices: list[float]) -> float:
        """Calculate maximum drawdown using vectorized operations."""
        if not prices:
            return 0.0

        price_array = np.array(prices, dtype=np.float64)
        cummax = np.maximum.accumulate(price_array)
        drawdown = (price_array - cummax) / cummax

        return float(np.min(drawdown))

    @staticmethod
    def calculate_bollinger_bands(
        prices: list[float],
        window: int = 20,
        num_std: float = 2.0,
    ) -> tuple[list[float], list[float], list[float]]:
        """Calculate Bollinger Bands using vectorized operations."""
        if not prices or len(prices) < window:
            return [], [], []

        price_array = np.array(prices, dtype=np.float64)
        ma = np.convolve(price_array, np.ones(window) / window, mode='valid')

        rolling_std = np.array([
            np.std(price_array[max(0, i - window):i + 1], ddof=1)
            for i in range(window - 1, len(price_array))
        ])

        upper = ma + (rolling_std * num_std)
        lower = ma - (rolling_std * num_std)

        return upper.tolist(), ma.tolist(), lower.tolist()

    @staticmethod
    def batch_calculate_returns(price_lists: list[list[float]]) -> list[list[float]]:
        """Batch calculate returns for multiple securities."""
        return [
            VectorizedCalculator.calculate_returns(prices)
            for prices in price_lists
        ]

    @staticmethod
    def batch_calculate_volatility(
        price_lists: list[list[float]],
        window: int = 20,
    ) -> list[float]:
        """Batch calculate volatility for multiple securities."""
        return [
            VectorizedCalculator.calculate_volatility(prices, window)
            for prices in price_lists
            if len(prices) >= window
        ]

    @staticmethod
    def calculate_rolling_correlation(
        series1: list[float],
        series2: list[float],
        window: int = 20,
    ) -> list[float]:
        """Calculate rolling correlation using vectorized operations."""
        if len(series1) != len(series2) or len(series1) < window:
            return []

        arr1 = np.array(series1, dtype=np.float64)
        arr2 = np.array(series2, dtype=np.float64)
        n = len(arr1)

        result = np.full(n, np.nan)

        for i in range(window - 1, n):
            sub1 = arr1[i - window + 1:i + 1]
            sub2 = arr2[i - window + 1:i + 1]

            if np.std(sub1) > 0 and np.std(sub2) > 0:
                corr = np.corrcoef(sub1, sub2)[0, 1]
                result[i] = corr if not np.isnan(corr) else 0.0

        return result.tolist()

    @staticmethod
    def calculate_rolling_beta(
        returns: list[float],
        benchmark: list[float],
        window: int = 60,
    ) -> list[float]:
        """Calculate rolling beta against benchmark."""
        if len(returns) != len(benchmark) or len(returns) < window:
            return []

        ret_arr = np.array(returns, dtype=np.float64)
        ben_arr = np.array(benchmark, dtype=np.float64)
        n = len(ret_arr)

        result = np.full(n, np.nan)

        for i in range(window - 1, n):
            sub_ret = ret_arr[i - window + 1:i + 1]
            sub_ben = ben_arr[i - window + 1:i + 1]

            var_ben = np.var(sub_ben)
            if var_ben > 0:
                cov = np.cov(sub_ret, sub_ben)[0, 1]
                result[i] = cov / var_ben

        return result.tolist()

    @staticmethod
    def calculate_cross_sectional_rank(values: list[list[float]]) -> list[list[float]]:
        """Calculate cross-sectional rank for each timestep.

        Args:
            values: List of security values at each timestep

        Returns:
            Rank normalized to [0, 1] for each timestep
        """
        if not values:
            return []

        n_timesteps = len(values)
        result = []

        for t in range(n_timesteps):
            arr = np.array(values[t], dtype=np.float64)
            if len(arr) == 0:
                result.append([])
                continue

            ranks = np.argsort(np.argsort(arr)) / (len(arr) - 1)
            result.append(ranks.tolist())

        return result

    @staticmethod
    def calculate_decay_weighted_sum(
        values: list[float],
        half_life: int = 20,
    ) -> float:
        """Calculate exponentially decay-weighted sum."""
        if not values:
            return 0.0

        arr = np.array(values, dtype=np.float64)
        n = len(arr)
        weights = np.exp(-np.arange(n) * np.log(2) / half_life)

        return float(np.sum(arr * weights))

    @staticmethod
    def batch_calculate_ic(
        factor_matrix: list[list[float]],
        returns_matrix: list[list[float]],
    ) -> list[float]:
        """Batch calculate Information Coefficient for multiple factors.

        Args:
            factor_matrix: [n_factors, n_days] factor values
            returns_matrix: [n_factors, n_days] future returns

        Returns:
            List of IC values for each factor
        """
        if not factor_matrix or not returns_matrix:
            return []

        ic_values = []
        for factor, ret in zip(factor_matrix, returns_matrix):
            if len(factor) != len(ret) or len(factor) < 2:
                ic_values.append(0.0)
            else:
                corr = np.corrcoef(factor, ret)[0, 1]
                ic_values.append(corr if not np.isnan(corr) else 0.0)

        return ic_values

    @staticmethod
    def calculate_alpha_momentum_score(
        prices: list[float],
        short_window: int = 5,
        long_window: int = 20,
    ) -> float:
        """Calculate momentum score (short vs long term).

        Returns value in [-1, 1]:
        - Positive: bullish (short > long)
        - Negative: bearish (short < long)
        """
        if len(prices) < long_window:
            return 0.0

        price_arr = np.array(prices, dtype=np.float64)
        short_ret = (price_arr[-1] - price_arr[-short_window]) / price_arr[-short_window] if short_window > 0 else 0.0
        long_ret = (price_arr[-1] - price_arr[-long_window]) / price_arr[-long_window] if long_window > 0 else 0.0

        return float(np.tanh(short_ret - long_ret))


class PerformanceOptimizer:
    """Optimizer for large-scale market scanning.

    Provides zero-copy transfer mechanisms and efficient memory management
    for processing 5000+ securities.
    """

    @staticmethod
    def scan_by_criteria(
        securities: list[dict[str, Any]],
        criteria: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Scan securities by multiple criteria using vectorized operations.

        Returns list of dicts (DTO-like) instead of DataFrame for efficient
        transfer to presentation layer.
        """
        if not securities:
            return []

        symbols = [s.get("code") or s.get("symbol") for s in securities]
        prices = [s.get("price", 0) or 0 for s in securities]
        volumes = [s.get("volume", 0) or 0 for s in securities]
        changes = [s.get("change_pct", 0) or 0 for s in securities]

        np.array(symbols, dtype=object)
        prices_arr = np.array(prices, dtype=np.float64)
        volumes_arr = np.array(volumes, dtype=np.float64)
        changes_arr = np.array(changes, dtype=np.float64)

        mask = np.ones(len(securities), dtype=bool)

        if "min_price" in criteria:
            mask &= (prices_arr >= criteria["min_price"])
        if "max_price" in criteria:
            mask &= (prices_arr <= criteria["max_price"])
        if "min_volume" in criteria:
            mask &= (volumes_arr >= criteria["min_volume"])
        if "min_change_pct" in criteria:
            mask &= (changes_arr >= criteria["min_change_pct"])
        if "max_change_pct" in criteria:
            mask &= (changes_arr <= criteria["max_change_pct"])

        filtered_indices = np.where(mask)[0]

        result = []
        for idx in filtered_indices:
            result.append({
                "code": securities[idx].get("code"),
                "name": securities[idx].get("name"),
                "price": securities[idx].get("price"),
                "change_pct": securities[idx].get("change_pct"),
                "volume": securities[idx].get("volume"),
            })

        return result

    @staticmethod
    def rank_securities(
        securities: list[dict[str, Any]],
        sort_by: str = "volume",
        ascending: bool = False,
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rank securities by criteria and return top N."""
        if not securities:
            return []

        values = [s.get(sort_by, 0) or 0 for s in securities]
        values_arr = np.array(values, dtype=np.float64)

        if ascending:
            sorted_indices = np.argsort(values_arr)
        else:
            sorted_indices = np.argsort(-values_arr)

        if top_n:
            sorted_indices = sorted_indices[:top_n]

        result = []
        for idx in sorted_indices:
            result.append(securities[idx])

        return result


class MemoryEfficientProcessor:
    """Processor for efficient memory usage with large datasets."""

    @staticmethod
    def chunk_process(
        data: list[Any],
        chunk_size: int,
        processor: callable,
    ) -> list[Any]:
        """Process data in chunks to reduce memory pressure."""
        results = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_result = processor(chunk)
            results.extend(chunk_result)
        return results

    @staticmethod
    def to_dto_list(
        data: list[dict[str, Any]],
        dto_class: type | None = None,
    ) -> list[Any]:
        """Convert list of dicts to DTO list efficiently.

        This provides zero-copy-like transfer to presentation layer.
        """
        if dto_class is None:
            return data

        dtos = []
        for item in data:
            try:
                dto = dto_class(**item)
                dtos.append(dto)
            except Exception as e:
                logger.warning(f"Failed to create DTO: {e}")
                continue

        return dtos


def create_calculator() -> VectorizedCalculator:
    """Factory function to create vectorized calculator."""
    return VectorizedCalculator()


def create_optimizer() -> PerformanceOptimizer:
    """Factory function to create performance optimizer."""
    return PerformanceOptimizer()
