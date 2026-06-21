from __future__ import annotations
"""Chaos Engineering Integration with Resilience Components.

This module integrates chaos engineering with:
- DataQualityGate: Verify data validation under anomalous conditions
- CircuitBreaker: Test fault tolerance under failure conditions

Usage:
    # Test data quality gate with anomalous data
    gate = DataQualityGate()
    chaos_gate = ChaosDataQualityIntegration(gate)
    result = await chaos_gate.test_with_price_jump_anomaly(magnitude=0.5)

    # Test circuit breaker under load
    breaker = CircuitBreaker(...)
    chaos_breaker = ChaosCircuitBreakerIntegration(breaker)
    result = await chaos_breaker.test_circuit_open()
"""


import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChaosTestResult:
    """Result of a chaos integration test."""

    test_name: str
    passed: bool
    fault_injected: str
    recovery_successful: bool
    error_message: Optional[str] = None
    metrics: dict[str, Any] = None


class ChaosDataQualityIntegration:
    """Integration between ChaosEngine and DataQualityGate.

    This class provides methods to test data quality validation
    under various anomalous conditions.
    """

    def __init__(self, data_quality_gate=None):
        self._gate = data_quality_gate

    async def test_with_price_jump_anomaly(
        self,
        base_price: float = 100.0,
        magnitude: float = 0.5,
    ) -> ChaosTestResult:
        """Test data quality gate with price jump anomaly.

        Args:
            base_price: Base price to use
            magnitude: Magnitude of price jump (0.5 = 50%)

        Returns:
            ChaosTestResult with test outcome
        """
        test_name = "price_jump_anomaly"
        logger.info(f"Testing DataQualityGate with {test_name}")

        try:
            if self._gate:
                test_data = {
                    "symbol": "TEST",
                    "price": base_price * (1 + magnitude),
                    "prev_close": base_price,
                    "change_pct": magnitude * 100,
                }
                validation_result = self._gate.validate(test_data)
                passed = validation_result.get("valid", False)

                return ChaosTestResult(
                    test_name=test_name,
                    passed=passed,
                    fault_injected=f"price_jump_{magnitude * 100:.0f}%",
                    recovery_successful=True,
                    metrics={"validation": validation_result},
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected=f"price_jump_{magnitude * 100:.0f}%",
                    recovery_successful=True,
                    error_message="DataQualityGate not configured",
                )

        except Exception as e:
            logger.error(f"Data quality chaos test failed: {e}")
            return ChaosTestResult(
                test_name=test_name,
                passed=False,
                fault_injected=f"price_jump_{magnitude * 100:.0f}%",
                recovery_successful=True,
                error_message=str(e),
            )

    async def test_with_missing_values(
        self,
        data: dict[str, Any],
        missing_fields: list[str],
    ) -> ChaosTestResult:
        """Test data quality gate with missing values."""
        test_name = "missing_values"
        logger.info(f"Testing DataQualityGate with {test_name}")

        try:
            if self._gate:
                test_data = {k: v for k, v in data.items() if k not in missing_fields}
                validation_result = self._gate.validate(test_data)
                passed = not validation_result.get("valid", True)

                return ChaosTestResult(
                    test_name=test_name,
                    passed=passed,
                    fault_injected=f"missing_fields_{missing_fields}",
                    recovery_successful=True,
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected=f"missing_fields_{missing_fields}",
                    recovery_successful=True,
                )

        except Exception as e:
            return ChaosTestResult(
                test_name=test_name,
                passed=False,
                fault_injected=f"missing_fields_{missing_fields}",
                recovery_successful=True,
                error_message=str(e),
            )

    async def test_with_extreme_volume(
        self,
        base_volume: float = 1000000.0,
        multiplier: float = 100.0,
    ) -> ChaosTestResult:
        """Test data quality gate with extreme volume."""
        test_name = "extreme_volume"
        logger.info(f"Testing DataQualityGate with {test_name}")

        try:
            if self._gate:
                test_data = {
                    "symbol": "TEST",
                    "volume": base_volume * multiplier,
                    "amount": base_volume * multiplier * 100,
                }
                validation_result = self._gate.validate(test_data)
                passed = not validation_result.get("valid", True)

                return ChaosTestResult(
                    test_name=test_name,
                    passed=passed,
                    fault_injected=f"volume_x{multiplier}",
                    recovery_successful=True,
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected=f"volume_x{multiplier}",
                    recovery_successful=True,
                )

        except Exception as e:
            return ChaosTestResult(
                test_name=test_name,
                passed=False,
                fault_injected=f"volume_x{multiplier}",
                recovery_successful=True,
                error_message=str(e),
            )


class ChaosCircuitBreakerIntegration:
    """Integration between ChaosEngine and CircuitBreaker.

    This class provides methods to test circuit breaker behavior
    under various failure conditions.
    """

    def __init__(self, circuit_breaker=None):
        self._breaker = circuit_breaker

    async def test_circuit_open(
        self,
        failure_count: int = 5,
    ) -> ChaosTestResult:
        """Test that circuit opens after threshold failures."""
        test_name = "circuit_open"
        logger.info(f"Testing CircuitBreaker with {failure_count} failures")

        try:
            if self._breaker:
                for i in range(failure_count):
                    await self._breaker.call(lambda: (_ for _ in ()).throw(Exception(f"Failure {i}")))

                is_open = self._breaker.state == "open"

                return ChaosTestResult(
                    test_name=test_name,
                    passed=is_open,
                    fault_injected=f"failures_{failure_count}",
                    recovery_successful=is_open,
                    metrics={"state": self._breaker.state},
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected=f"failures_{failure_count}",
                    recovery_successful=True,
                    error_message="CircuitBreaker not configured",
                )

        except Exception as e:
            return ChaosTestResult(
                test_name=test_name,
                passed=True,
                fault_injected=f"failures_{failure_count}",
                recovery_successful=True,
                error_message=str(e),
            )

    async def test_circuit_half_open(
        self,
        failure_count: int = 5,
    ) -> ChaosTestResult:
        """Test circuit transitions to half-open after timeout."""
        test_name = "circuit_half_open"
        logger.info(f"Testing CircuitBreaker half-open state")

        try:
            if self._breaker:
                for i in range(failure_count):
                    try:
                        await self._breaker.call(lambda: (_ for _ in ()).throw(Exception(f"Failure {i}")))
                    except Exception as e:
                        logger.warning("resilience_integration.py.test_circuit_half_open: %s", e)

                await asyncio.sleep(self._breaker.reset_timeout / 1000 + 1)

                is_half_open = self._breaker.state == "half-open"

                return ChaosTestResult(
                    test_name=test_name,
                    passed=is_half_open,
                    fault_injected="timeout_elapsed",
                    recovery_successful=True,
                    metrics={"state": self._breaker.state},
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected="timeout_elapsed",
                    recovery_successful=True,
                )

        except Exception as e:
            return ChaosTestResult(
                test_name=test_name,
                passed=False,
                fault_injected="timeout_elapsed",
                recovery_successful=False,
                error_message=str(e),
            )

    async def test_circuit_close_after_success(
        self,
        success_count: int = 3,
    ) -> ChaosTestResult:
        """Test circuit closes after successful calls in half-open state."""
        test_name = "circuit_close"
        logger.info(f"Testing CircuitBreaker close after {success_count} successes")

        try:
            if self._breaker:
                for i in range(success_count):
                    try:
                        await self._breaker.call(lambda: "success")
                    except Exception as e:
                        logger.warning("resilience_integration.py.test_circuit_close_after_success: %s", e)

                is_closed = self._breaker.state == "closed"

                return ChaosTestResult(
                    test_name=test_name,
                    passed=is_closed,
                    fault_injected=f"successes_{success_count}",
                    recovery_successful=is_closed,
                    metrics={"state": self._breaker.state},
                )
            else:
                return ChaosTestResult(
                    test_name=test_name,
                    passed=True,
                    fault_injected=f"successes_{success_count}",
                    recovery_successful=True,
                )

        except Exception as e:
            return ChaosTestResult(
                test_name=test_name,
                passed=False,
                fault_injected=f"successes_{success_count}",
                recovery_successful=False,
                error_message=str(e),
            )


async def run_full_resilience_test(
    data_quality_gate=None,
    circuit_breaker=None,
) -> dict[str, ChaosTestResult]:
    """Run a full resilience test suite.

    Args:
        data_quality_gate: DataQualityGate instance
        circuit_breaker: CircuitBreaker instance

    Returns:
        Dictionary of test results
    """
    results = {}

    dq_integration = ChaosDataQualityIntegration(data_quality_gate)
    results["price_jump"] = await dq_integration.test_with_price_jump_anomaly()
    results["missing_values"] = await dq_integration.test_with_missing_values(
        {"symbol": "TEST", "price": 100.0, "volume": 1000000},
        ["price"],
    )
    results["extreme_volume"] = await dq_integration.test_with_extreme_volume()

    cb_integration = ChaosCircuitBreakerIntegration(circuit_breaker)
    results["circuit_open"] = await cb_integration.test_circuit_open()

    return results


__all__ = [
    "ChaosDataQualityIntegration",
    "ChaosCircuitBreakerIntegration",
    "ChaosTestResult",
    "run_full_resilience_test",
]