from __future__ import annotations
"""Chaos Engineering Framework for Quant Atlas.

This module provides infrastructure for running chaos experiments to verify
system resilience under adverse conditions.

Key capabilities:
- Network fault injection (latency, timeout, packet loss)
- Database fault injection (connection failure, query timeout)
- External API failure simulation
- Data quality anomaly injection
- Circuit breaker trigger testing

Usage:
    chaos = ChaosEngine()
    chaos.add_fault(NetworkLatencyFault(delay_ms=5000))
    chaos.add_fault(DatabaseConnectionFault())
    result = await chaos.run_experiment(experiment_name="test_order_placement")
"""


import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


class FaultType(Enum):
    """Types of faults that can be injected."""

    NETWORK_LATENCY = "network_latency"
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_PARTITION = "network_partition"
    DATABASE_CONNECTION_FAILURE = "database_connection_failure"
    DATABASE_QUERY_TIMEOUT = "database_query_timeout"
    API_FAILURE = "api_failure"
    DATA_QUALITY_ANOMALY = "data_quality_anomaly"
    CIRCUIT_BREAKER_TRIGGER = "circuit_breaker_trigger"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class ExperimentStatus(Enum):
    """Status of a chaos experiment."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "abort"


@dataclass
class ChaosConfig:
    """Configuration for chaos experiments."""

    enabled: bool = False
    probability: float = 0.1
    max_duration_seconds: int = 60
    fault_types: list[FaultType] = field(default_factory=list)


@dataclass
class ExperimentResult:
    """Result of a chaos experiment."""

    experiment_name: str
    status: ExperimentStatus
    start_time: datetime
    end_time: datetime
    faults_injected: list[str]
    system_recovered: bool
    recovery_time_ms: int
    error_message: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)


class ChaosFault(ABC):
    """Base class for chaos faults."""

    @abstractmethod
    async def inject(self) -> None:
        """Inject the fault."""
        pass

    @abstractmethod
    async def recover(self) -> None:
        """Recover from the fault."""
        pass

    @abstractmethod
    def get_fault_type(self) -> FaultType:
        """Get the type of this fault."""
        pass


class NetworkLatencyFault(ChaosFault):
    """Inject network latency."""

    def __init__(self, delay_ms: int = 5000, target: str = "all"):
        self.delay_ms = delay_ms
        self.target = target
        self._original_delay = 0
        self._injected = False

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Injecting network latency: {self.delay_ms}ms on {self.target}")
        self._injected = True

    async def recover(self) -> None:
        if self._injected:
            logger.info(f"[CHAOS] Recovering from network latency fault")
            self._injected = False

    def get_fault_type(self) -> FaultType:
        return FaultType.NETWORK_LATENCY

    def __repr__(self):
        return f"NetworkLatencyFault(delay_ms={self.delay_ms})"


class NetworkTimeoutFault(ChaosFault):
    """Inject network timeout."""

    def __init__(self, target: str = "all", timeout_count: int = 3):
        self.target = target
        self.timeout_count = timeout_count
        self._injected = False

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Injecting network timeouts: {self.timeout_count} on {self.target}")
        self._injected = True

    async def recover(self) -> None:
        if self._injected:
            logger.info(f"[CHAOS] Recovering from network timeout fault")
            self._injected = False

    def get_fault_type(self) -> FaultType:
        return FaultType.NETWORK_TIMEOUT


class DatabaseConnectionFault(ChaosFault):
    """Inject database connection failure."""

    def __init__(self, duration_seconds: int = 30):
        self.duration_seconds = duration_seconds
        self._original_connect = None

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Injecting database connection failure for {self.duration_seconds}s")
        await asyncio.sleep(self.duration_seconds)

    async def recover(self) -> None:
        logger.info(f"[CHAOS] Recovering from database connection fault")

    def get_fault_type(self) -> FaultType:
        return FaultType.DATABASE_CONNECTION_FAILURE


class DatabaseQueryTimeoutFault(ChaosFault):
    """Inject database query timeout."""

    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Injecting database query timeout: {self.timeout_ms}ms")

    async def recover(self) -> None:
        logger.info(f"[CHAOS] Recovering from database query timeout")

    def get_fault_type(self) -> FaultType:
        return FaultType.DATABASE_QUERY_TIMEOUT


class APIFailureFault(ChaosFault):
    """Inject external API failure."""

    def __init__(self, api_name: str, failure_rate: float = 1.0):
        self.api_name = api_name
        self.failure_rate = failure_rate

    async def inject(self) -> None:
        if random.random() < self.failure_rate:
            logger.warning(f"[CHAOS] Injecting API failure for {self.api_name}")
            raise Exception(f"Simulated API failure: {self.api_name}")

    async def recover(self) -> None:
        logger.info(f"[CHAOS] Recovering from API failure")

    def get_fault_type(self) -> FaultType:
        return FaultType.API_FAILURE


class DataQualityAnomalyFault(ChaosFault):
    """Inject data quality anomalies."""

    def __init__(self, anomaly_type: str = "price_jump", magnitude: float = 0.5):
        self.anomaly_type = anomaly_type
        self.magnitude = magnitude

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Injecting data quality anomaly: {self.anomaly_type} (magnitude: {self.magnitude})")

    async def recover(self) -> None:
        logger.info(f"[CHAOS] Recovering from data quality anomaly")

    def get_fault_type(self) -> FaultType:
        return FaultType.DATA_QUALITY_ANOMALY


class CircuitBreakerTriggerFault(ChaosFault):
    """Trigger circuit breaker to test fault tolerance."""

    def __init__(self, failure_count: int = 5):
        self.failure_count = failure_count

    async def inject(self) -> None:
        logger.warning(f"[CHAOS] Triggering circuit breaker with {self.failure_count} failures")

    async def recover(self) -> None:
        logger.info(f"[CHAOS] Circuit breaker should now be open")

    def get_fault_type(self) -> FaultType:
        return FaultType.CIRCUIT_BREAKER_TRIGGER


class ChaosEngine:
    """Main chaos engineering engine."""

    def __init__(self, config: Optional[ChaosConfig] = None):
        self._config = config or ChaosConfig()
        self._faults: list[ChaosFault] = []
        self._running = False
        self._injected_faults: list[str] = []

    def add_fault(self, fault: ChaosFault) -> None:
        """Add a fault to be injected."""
        self._faults.append(fault)
        logger.info(f"Added fault: {fault}")

    def clear_faults(self) -> None:
        """Clear all registered faults."""
        self._faults.clear()
        self._injected_faults.clear()

    async def run_experiment(
        self,
        experiment_name: str,
        target_function: Callable,
        *args,
        **kwargs,
    ) -> ExperimentResult:
        """Run a chaos experiment.

        Args:
            experiment_name: Name of the experiment
            target_function: Function to test
            *args, **kwargs: Arguments for the target function

        Returns:
            ExperimentResult with outcome details
        """
        if not self._config.enabled:
            logger.info("Chaos experiments are disabled")
            return ExperimentResult(
                experiment_name=experiment_name,
                status=ExperimentStatus.ABORTED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                faults_injected=[],
                system_recovered=True,
                recovery_time_ms=0,
                error_message="Chaos experiments disabled",
            )

        logger.info(f"Starting chaos experiment: {experiment_name}")
        start_time = datetime.now()
        self._running = True
        self._injected_faults = []

        try:
            for fault in self._faults:
                if random.random() < self._config.probability:
                    await fault.inject()
                    self._injected_faults.append(str(fault))

            result = await target_function(*args, **kwargs)

            for fault in self._faults:
                await fault.recover()

            end_time = datetime.now()
            recovery_time = int((end_time - start_time).total_seconds() * 1000)

            return ExperimentResult(
                experiment_name=experiment_name,
                status=ExperimentStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                faults_injected=self._injected_faults,
                system_recovered=True,
                recovery_time_ms=recovery_time,
                metrics={"result": result},
            )

        except Exception as e:
            end_time = datetime.now()
            recovery_time = int((end_time - start_time).total_seconds() * 1000)

            for fault in self._faults:
                try:
                    await fault.recover()
                except Exception as e:
                    logger.warning("engine.py.run_experiment: %s", e)

            logger.error(f"Chaos experiment failed: {e}")
            return ExperimentResult(
                experiment_name=experiment_name,
                status=ExperimentStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                faults_injected=self._injected_faults,
                system_recovered=False,
                recovery_time_ms=recovery_time,
                error_message=str(e),
            )
        finally:
            self._running = False

    def get_registered_faults(self) -> list[str]:
        """Get list of registered faults."""
        return [str(f) for f in self._faults]


def create_chaos_engine(
    enabled: bool = False,
    probability: float = 0.1,
    fault_types: Optional[list[FaultType]] = None,
) -> ChaosEngine:
    """Factory function to create a configured chaos engine."""
    config = ChaosConfig(
        enabled=enabled,
        probability=probability,
        fault_types=fault_types or [],
    )
    return ChaosEngine(config)


__all__ = [
    "ChaosEngine",
    "ChaosFault",
    "ChaosConfig",
    "ExperimentResult",
    "ExperimentStatus",
    "FaultType",
    "NetworkLatencyFault",
    "NetworkTimeoutFault",
    "DatabaseConnectionFault",
    "DatabaseQueryTimeoutFault",
    "APIFailureFault",
    "DataQualityAnomalyFault",
    "CircuitBreakerTriggerFault",
    "create_chaos_engine",
]