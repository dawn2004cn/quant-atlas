from __future__ import annotations
"""AI Hedge Fund Integration - bridges ai-hedge-fund multi-agent system into Quant Atlas.

This module integrates the ai-hedge-fund agents as Quant Atlas's "Intelligent Research Team":
1. AI-Hedge-Fund Agents produce multi-agent investment perspectives
2. Signals are forwarded to RD_Agent/Qlib for strategy validation
3. Validated results are exposed for UI display

Architecture:
    AI-Hedge-Fund Agents -> Signal Aggregation -> RD-Agent Validation -> Qlib Backtest -> UI Display
"""


from .service import AIHedgeFundIntegrationService
from .adapters import (
    HedgeFundAgentAdapter,
    RDAgentValidationAdapter,
    QlibValidationAdapter,
)
from .dto import (
    HedgeFundAnalysisRequest,
    HedgeFundAnalysisResult,
    AgentSignal,
    ValidationResult,
)

__all__ = [
    "AIHedgeFundIntegrationService",
    "HedgeFundAgentAdapter",
    "RDAgentValidationAdapter",
    "QlibValidationAdapter",
    "HedgeFundAnalysisRequest",
    "HedgeFundAnalysisResult",
    "AgentSignal",
    "ValidationResult",
]
