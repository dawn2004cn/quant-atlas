"""Execution module."""

from .high_fidelity_engine import (
    ExecutionResult,
    SlippageModel,
    TickSimulator,
    ConsistencyAuditor,
    HighFidelityExecutor,
    get_high_fidelity_executor,
)

from .digital_twin import (
    StrategyState,
    DriftAnalysis,
    ShadowStrategy,
    DriftDetector,
    AutoHotSwap,
    DigitalTwin,
    get_digital_twin,
)

__all__ = [
    "ExecutionResult",
    "SlippageModel",
    "TickSimulator",
    "ConsistencyAuditor",
    "HighFidelityExecutor",
    "get_high_fidelity_executor",
    "StrategyState",
    "DriftAnalysis",
    "ShadowStrategy",
    "DriftDetector",
    "AutoHotSwap",
    "DigitalTwin",
    "get_digital_twin",
]