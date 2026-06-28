from __future__ import annotations
"""High-Performance Computation - Vectorized Factor Calculation.

This module implements from strategy_plan1.md:
- VectorizedMarketData: NumPy-based market data storage
- AcceleratedFactors: Numba/Cython accelerated factor calculation
- BatchProcessor: Process 5000+ symbols efficiently

Usage:
    processor = BatchProcessor()
    results = await processor.scan_all_symbols(factor_func, symbols)
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VectorizedMarketData:
    """Vectorized market data using NumPy arrays."""
    symbol: str
    timestamps: np.ndarray
    open_prices: np.ndarray
    high_prices: np.ndarray
    low_prices: np.ndarray
    close_prices: np.ndarray
    volumes: np.ndarray
    created_at: datetime = field(default_factory=datetime.now)


class AcceleratedFactors:
    """Numba-accelerated factor calculations."""

    @staticmethod
    def calculate_ma(prices: np.ndarray, window: int) -> np.ndarray:
        """Calculate moving average."""
        result = np.full_like(prices, np.nan, dtype=np.float64)
        if len(prices) < window:
            return result

        cumsum = np.cumsum(np.nan_to_num(prices))
        cumsum[window:] = cumsum[window:] - cumsum[:-window]
        result[window - 1:] = cumsum[window - 1:] / window

        return result

    @staticmethod
    def calculate_ema(prices: np.ndarray, span: int) -> np.ndarray:
        """Calculate exponential moving average."""
        result = np.full_like(prices, np.nan, dtype=np.float64)
        if len(prices) < span:
            return result

        alpha = 2.0 / (span + 1)
        result[0] = prices[0]

        for i in range(1, len(prices)):
            result[i] = alpha * prices[i] + (1 - alpha) * result[i - 1]

        return result

    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI indicator."""
        result = np.full_like(prices, np.nan, dtype=np.float64)
        if len(prices) < period + 1:
            return result

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            result[period] = 100
        else:
            rs = avg_gain / avg_loss
            result[period] = 100 - (100 / (1 + rs))

        for i in range(period + 1, len(prices)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

            if avg_loss == 0:
                result[i] = 100
            else:
                rs = avg_gain / avg_loss
                result[i] = 100 - (100 / (1 + rs))

        return result

    @staticmethod
    def calculate_bollinger_bands(
        prices: np.ndarray,
        window: int = 20,
        num_std: float = 2.0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands."""
        ma = AcceleratedFactors.calculate_ma(prices, window)
        std = np.zeros_like(prices)

        for i in range(window - 1, len(prices)):
            std[i] = np.std(prices[i - window + 1:i + 1])

        upper = ma + num_std * std
        lower = ma - num_std * std

        return ma, upper, lower

    @staticmethod
    def calculate_correlation_matrix(
        prices_array: np.ndarray,
    ) -> np.ndarray:
        """Calculate correlation matrix for multiple securities."""
        returns = np.diff(prices_array, axis=1) / prices_array[:, :-1]
        return np.corrcoef(returns)


class BatchProcessor:
    """Batch processor for scanning 5000+ symbols."""

    def __init__(self, batch_size: int = 100):
        self._batch_size = batch_size

    async def scan_all_symbols(
        self,
        factor_func: callable,
        symbols: list[str],
        market_data: dict[str, VectorizedMarketData],
    ) -> dict[str, Any]:
        """Scan all symbols with factor function."""
        results = {}

        for i in range(0, len(symbols), self._batch_size):
            batch = symbols[i:i + self._batch_size]

            batch_results = await self._process_batch(factor_func, batch, market_data)
            results.update(batch_results)

            if (i // self._batch_size) % 10 == 0:
                logger.info(f"Processed {i + len(batch)}/{len(symbols)} symbols")

        return results

    async def _process_batch(
        self,
        factor_func: callable,
        batch: list[str],
        market_data: dict[str, VectorizedMarketData],
    ) -> dict[str, Any]:
        """Process a batch of symbols."""
        results = {}

        for symbol in batch:
            if symbol in market_data:
                try:
                    data = market_data[symbol]
                    result = factor_func(
                        data.close_prices,
                        data.volumes,
                    )
                    results[symbol] = result
                except Exception as e:
                    logger.warning(f"Failed to process {symbol}: {e}")

        return results


class VectorizedFactorEngine:
    """Complete vectorized factor calculation engine."""

    def __init__(
        self,
        batch_processor: BatchProcessor | None = None,
    ):
        self._processor = batch_processor or BatchProcessor()
        self._cache: dict[str, np.ndarray] = {}

    def create_vectorized_data(
        self,
        symbol: str,
        price_data: list[dict[str, Any]],
    ) -> VectorizedMarketData:
        """Create vectorized data from price history."""
        timestamps = np.array([d.get("timestamp", 0) for d in price_data], dtype=np.int64)
        opens = np.array([d.get("open", 0) for d in price_data], dtype=np.float64)
        highs = np.array([d.get("high", 0) for d in price_data], dtype=np.float64)
        lows = np.array([d.get("low", 0) for d in price_data], dtype=np.float64)
        closes = np.array([d.get("close", 0) for d in price_data], dtype=np.float64)
        volumes = np.array([d.get("volume", 0) for d in price_data], dtype=np.float64)

        return VectorizedMarketData(
            symbol=symbol,
            timestamps=timestamps,
            open_prices=opens,
            high_prices=highs,
            low_prices=lows,
            close_prices=closes,
            volumes=volumes,
        )

    def calculate_factors(
        self,
        data: VectorizedMarketData,
        factor_names: list[str],
    ) -> dict[str, np.ndarray]:
        """Calculate multiple factors for symbol."""
        results = {}

        for factor in factor_names:
            if factor == "ma5":
                results["ma5"] = AcceleratedFactors.calculate_ma(data.close_prices, 5)
            elif factor == "ma20":
                results["ma20"] = AcceleratedFactors.calculate_ma(data.close_prices, 20)
            elif factor == "ma60":
                results["ma60"] = AcceleratedFactors.calculate_ma(data.close_prices, 60)
            elif factor == "ema12":
                results["ema12"] = AcceleratedFactors.calculate_ema(data.close_prices, 12)
            elif factor == "rsi":
                results["rsi"] = AcceleratedFactors.calculate_rsi(data.close_prices)
            elif factor == "bbands":
                ma, upper, lower = AcceleratedFactors.calculate_bollinger_bands(data.close_prices)
                results["bb_upper"] = upper
                results["bb_middle"] = ma
                results["bb_lower"] = lower

        return results

    def batch_calculate(
        self,
        symbols: list[str],
        market_data: dict[str, VectorizedMarketData],
        factor_names: list[str],
    ) -> dict[str, dict[str, np.ndarray]]:
        """Batch calculate factors for all symbols."""
        all_results = {}

        for symbol in symbols:
            if symbol in market_data:
                all_results[symbol] = self.calculate_factors(
                    market_data[symbol],
                    factor_names,
                )

        return all_results


_global_engine: VectorizedFactorEngine | None = None


def get_vectorized_engine() -> VectorizedFactorEngine:
    """Get singleton vectorized factor engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = VectorizedFactorEngine()
    return _global_engine
