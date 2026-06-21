"""Service factories for lifecycle optimization HTTP routes."""

from __future__ import annotations

from typing import Any


def get_tick_services() -> tuple[Any, Any, Any]:
    from app.modules.data.services.tick_data_service import (
        CrossSourceAlignmentService,
        DataLineageService,
        TickService,
    )

    return TickService(), DataLineageService(), CrossSourceAlignmentService()


def get_alpha_mining_services() -> tuple[Any, Any, Any]:
    from app.modules.strategy.services.alpha_mining_service import (
        AutoAlphaMiningService,
        CrossSectionalAnalysisService,
        ParameterSensitivityService,
    )

    return AutoAlphaMiningService(), ParameterSensitivityService(), CrossSectionalAnalysisService()


def get_simulation_services() -> tuple[Any, Any, Any]:
    from app.modules.strategy.services.simulation_service import (
        HftSimulatorService,
        MonteCarloService,
        WalkForwardService,
    )

    return HftSimulatorService(), WalkForwardService(), MonteCarloService()


def get_execution_services() -> tuple[Any, Any, Any]:
    from app.modules.execution.services.smart_execution_service import (
        ExecutionAlgorithmService,
        HardCircuitBreaker,
        SmartOrderRouter,
    )

    return SmartOrderRouter(), ExecutionAlgorithmService(), HardCircuitBreaker()


def get_monitoring_services() -> tuple[Any, Any, Any, Any]:
    from app.modules.system.services.monitoring_evolution_service import (
        AutoRebalanceService,
        ConceptDriftService,
        DeepAttributionService,
        RLHFTradingService,
    )

    return ConceptDriftService(), DeepAttributionService(), AutoRebalanceService(), RLHFTradingService()
