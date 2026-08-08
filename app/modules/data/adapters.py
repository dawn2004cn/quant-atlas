"""Data Service Adapters.

Adapters implement the Data Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.data.ports import (
    DataInfrastructurePort,
    DataLakePort,
    DataOptimizerPort,
    DataQualityPort,
    HistoricalResonancePort,
    MemoryOptimizationPort,
    PyTdxPort,
    QlibPort,
    TaskPipelinePort,
    TruthBadgePort,
)


class DataInfrastructureAdapter(DataInfrastructurePort):
    """Adapts data infrastructure service to DataInfrastructurePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_status(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_status()
        return {"status": "ok", "services": {}}


class DataLakeAdapter(DataLakePort):
    """Adapts data lake service to DataLakePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.query(query)
        return {"result": {}}


class DataOptimizerAdapter(DataOptimizerPort):
    """Adapts data optimizer service to DataOptimizerPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.run(params)
        return {"result": {}}


class DataQualityAdapter(DataQualityPort):
    """Adapts data quality service to DataQualityPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def verify(self, source: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.verify(source)
        return {"quality": 1.0}


class HistoricalResonanceAdapter(HistoricalResonancePort):
    """Adapts historical resonance service to HistoricalResonancePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_resonance(self, symbol: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_resonance(symbol)
        return {"resonance": {}}


class MemoryOptimizationAdapter(MemoryOptimizationPort):
    """Adapts memory optimization service to MemoryOptimizationPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_optimization(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_optimization()
        return {"optimization": {}}


class PyTdxAdapter(PyTdxPort):
    """Adapts pytdx service to PyTdxPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def query(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.query(params)
        return {"result": {}}


class QlibAdapter(QlibPort):
    """Adapts Qlib service to QlibPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_research_data(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_research_data(params)
        return {"data": {}}


class TaskPipelineAdapter(TaskPipelinePort):
    """Adapts task pipeline service to TaskPipelinePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_status(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_status()
        return {"status": {}}


class TruthBadgeAdapter(TruthBadgePort):
    """Adapts truth badge service to TruthBadgePort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_badge(self, market: str, symbol: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_badge(market, symbol)
        return {"badge": {}}


def create_data_ports(ctx: Any) -> dict[str, Any]:
    """Create all data ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "data_infrastructure_service", None) is not None:
        ports["data_infrastructure"] = DataInfrastructureAdapter(
            ctx.data_infrastructure_service
        )

    if getattr(ctx, "data_lake_manager", None) is not None:
        ports["data_lake"] = DataLakeAdapter(ctx.data_lake_manager)

    if getattr(ctx, "data_optimizer_service", None) is not None:
        ports["data_optimizer"] = DataOptimizerAdapter(ctx.data_optimizer_service)

    if getattr(ctx, "data_truth_guardian_service", None) is not None:
        ports["data_quality"] = DataQualityAdapter(ctx.data_truth_guardian_service)

    if getattr(ctx, "historical_resonance_service", None) is not None:
        ports["historical_resonance"] = HistoricalResonanceAdapter(
            ctx.historical_resonance_service
        )

    if getattr(ctx, "memory_optimization_service", None) is not None:
        ports["memory_optimization"] = MemoryOptimizationAdapter(
            ctx.memory_optimization_service
        )

    if getattr(ctx, "tdx_base_read_service", None) is not None:
        ports["pytdx"] = PyTdxAdapter(ctx.tdx_base_read_service)

    if getattr(ctx, "qlib_pipeline_service", None) is not None:
        ports["qlib"] = QlibAdapter(ctx.qlib_pipeline_service)

    if getattr(ctx, "task_pipeline_service", None) is not None:
        ports["task_pipeline"] = TaskPipelineAdapter(ctx.task_pipeline_service)

    if getattr(ctx, "data_truth_guardian_service", None) is not None:
        ports["truth_badge"] = TruthBadgeAdapter(ctx.data_truth_guardian_service)

    return ports


__all__ = [
    "DataInfrastructurePort",
    "DataLakePort",
    "DataOptimizerPort",
    "DataQualityPort",
    "HistoricalResonancePort",
    "MemoryOptimizationPort",
    "PyTdxPort",
    "QlibPort",
    "TaskPipelinePort",
    "TruthBadgePort",
    "DataInfrastructureAdapter",
    "DataLakeAdapter",
    "DataOptimizerAdapter",
    "DataQualityAdapter",
    "HistoricalResonanceAdapter",
    "MemoryOptimizationAdapter",
    "PyTdxAdapter",
    "QlibAdapter",
    "TaskPipelineAdapter",
    "TruthBadgeAdapter",
    "create_data_ports",
]
