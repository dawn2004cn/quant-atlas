from __future__ import annotations
"""High-performance computation engine with Rust bridge."""


import asyncio
from typing import Any
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)


class ComputationEngine:
    """High-performance computation engine."""

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._rust_available = False
        self._check_rust_availability()
        logger.info(f"ComputationEngine initialized (Rust: {self._rust_available})")

    def _check_rust_availability(self):
        """Check if Rust computation module is available."""
        try:
            from app.infrastructure.rust_indicators import compute_technical_indicators
            self._rust_available = True
            logger.info("Rust computation module available")
        except ImportError:
            logger.warning("Rust computation not available, using NumPy fallback")
            self._rust_available = False

    def compute_indicators(
        self,
        prices: list[float],
        volumes: list[int] | None = None
    ) -> dict[str, float]:
        """Compute technical indicators with optimal method."""
        if self._rust_available and len(prices) > 100:
            return self._compute_with_rust(prices, volumes)
        return self._compute_with_numpy(prices, volumes)

    def _compute_with_rust(
        self,
        prices: list[float],
        volumes: list[int] | None = None
    ) -> dict[str, float]:
        """Compute using Rust for large datasets."""
        try:
            from app.infrastructure.rust_indicators import compute_technical_indicators
            result = compute_technical_indicators(prices, volumes or [])
            return result
        except Exception as e:
            logger.error(f"Rust computation failed: {e}")
            return self._compute_with_numpy(prices, volumes)

    def _compute_with_numpy(
        self,
        prices: list[float],
        volumes: list[int] | None = None
    ) -> dict[str, float]:
        """Compute using NumPy (fallback)."""
        arr = np.array(prices)
        result = {}

        if len(arr) >= 5:
            result["ma5"] = float(np.mean(arr[-5:]))
        if len(arr) >= 10:
            result["ma10"] = float(np.mean(arr[-10:]))
        if len(arr) >= 20:
            result["ma20"] = float(np.mean(arr[-20:]))
        if len(arr) >= 60:
            result["ma60"] = float(np.mean(arr[-60:]))

        if len(arr) >= 14:
            deltas = np.diff(arr)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            rs = avg_gain / (avg_loss + 1e-10)
            result["rsi"] = float(100 - (100 / (1 + rs)))

        if len(arr) >= 26:
            ema12 = self._ema(arr, 12)
            ema26 = self._ema(arr, 26)
            result["macd"] = float(ema12 - ema26)

        if len(arr) >= 20:
            result["boll_middle"] = float(np.mean(arr[-20:]))
            std = np.std(arr[-20:])
            result["boll_upper"] = result["boll_middle"] + 2 * std
            result["boll_lower"] = result["boll_middle"] - 2 * std

        if len(arr) >= 14:
            high = np.max(arr[-14:])
            low = np.min(arr[-14:])
            result["atr"] = float((high - low) / 14)

        return result

    def _ema(self, arr: np.ndarray, period: int) -> float:
        """Calculate EMA."""
        if len(arr) < period:
            return float(np.mean(arr))
        ema = np.mean(arr[:period])
        multiplier = 2 / (period + 1)
        for val in arr[period:]:
            ema = (val - ema) * multiplier + ema
        return float(ema)

    def compute_batch(
        self,
        data_list: list[dict[str, Any]],
        compute_fn: Callable[[dict], dict]
    ) -> list[dict]:
        """Compute batch with parallel processing."""
        futures = [
            self._executor.submit(compute_fn, data)
            for data in data_list
        ]
        return [f.result() for f in futures]

    async def compute_async(
        self,
        prices: list[float],
        volumes: list[int] | None = None
    ) -> dict[str, float]:
        """Compute indicators asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.compute_indicators(prices, volumes)
        )

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


class VectorizedCalculator:
    """Vectorized calculations for maximum performance."""

    @staticmethod
    def calculate_returns(prices: list[float]) -> list[float]:
        """Calculate returns vectorized."""
        arr = np.array(prices)
        returns = np.diff(arr) / arr[:-1] * 100
        return returns.tolist()

    @staticmethod
    def calculate_volatility(prices: list[float], window: int = 20) -> float:
        """Calculate volatility."""
        arr = np.array(prices)
        if len(arr) < window:
            return 0.0
        returns = np.diff(arr) / arr[:-1]
        return float(np.std(returns) * np.sqrt(252) * 100)

    @staticmethod
    def calculate_sharpe(
        returns: list[float],
        risk_free_rate: float = 0.03
    ) -> float:
        """Calculate Sharpe ratio."""
        arr = np.array(returns)
        if len(arr) == 0 or np.std(arr) == 0:
            return 0.0
        excess_returns = arr - risk_free_rate / 252
        return float(np.mean(excess_returns) / np.std(arr) * np.sqrt(252))

    @staticmethod
    def calculate_max_drawdown(prices: list[float]) -> tuple[float, int, int]:
        """Calculate max drawdown."""
        arr = np.array(prices)
        cummax = np.maximum.accumulate(arr)
        drawdown = (arr - cummax) / cummax * 100

        max_dd = float(np.min(drawdown))
        end_idx = int(np.argmin(drawdown))

        start_idx = 0
        for i in range(end_idx - 1, -1, -1):
            if arr[i] == cummax[end_idx]:
                start_idx = i
                break

        return max_dd, start_idx, end_idx


_computation_engine: ComputationEngine | None = None


def get_computation_engine() -> ComputationEngine:
    """Get global computation engine."""
    global _computation_engine
    if _computation_engine is None:
        _computation_engine = ComputationEngine()
    return _computation_engine


__all__ = [
    "ComputationEngine",
    "VectorizedCalculator",
    "get_computation_engine",
]
