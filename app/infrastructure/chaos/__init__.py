"""Chaos Engineering Module for Quant Atlas.

This module provides chaos engineering capabilities to verify system
resilience under adverse conditions.

Submodules:
- engine: Core chaos engine and fault implementations
- resilience_integration: Integration with DataQualityGate and CircuitBreaker

Quick Start:
    from app.infrastructure.chaos import ChaosEngine, create_chaos_engine

    # Create chaos engine with configuration
    chaos = create_chaos_engine(enabled=True, probability=0.3)
    chaos.add_fault(NetworkLatencyFault(delay_ms=2000))

    # Run experiment
    result = await chaos.run_experiment(
        experiment_name="test_order_placement",
        target_function=my_order_function,
    )
"""

from .engine import (
    APIFailureFault,
    ChaosConfig,
    ChaosEngine,
    ChaosFault,
    CircuitBreakerTriggerFault,
    DatabaseConnectionFault,
    DatabaseQueryTimeoutFault,
    DataQualityAnomalyFault,
    ExperimentResult,
    ExperimentStatus,
    FaultType,
    NetworkLatencyFault,
    NetworkTimeoutFault,
    create_chaos_engine,
)
from .resilience_integration import (
    ChaosCircuitBreakerIntegration,
    ChaosDataQualityIntegration,
    ChaosTestResult,
    run_full_resilience_test,
)

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
    "ChaosDataQualityIntegration",
    "ChaosCircuitBreakerIntegration",
    "ChaosTestResult",
    "run_full_resilience_test",
]
