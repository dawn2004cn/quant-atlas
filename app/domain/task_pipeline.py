from __future__ import annotations
"""Task Pipeline - implements workflow pattern for task orchestration.

This module implements the task pipeline concept from midify_plan7.md:
- Pipeline: Sequence of stages (data sync -> factor calc -> signal scan)
- Stage: Individual step in the pipeline
- PipelineExecutor: Executes pipelines with proper error handling

Following Pipeline pattern for explicit workflow management.
"""



from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from enum import Enum
from typing import Any, Callable

from app.core.logger import get_logger


logger = get_logger(__name__)


class PipelineStatus(Enum):
    """Status of a pipeline execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage_name: str
    status: StageStatus
    output: Any = None
    error: str | None = None
    duration_ms: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    pipeline_name: str
    status: PipelineStatus
    stages: list[StageResult] = field(default_factory=list)
    total_duration_ms: float = 0
    error: str | None = None
    output: Any = None

    @property
    def is_success(self) -> bool:
        return self.status == PipelineStatus.COMPLETED

    @property
    def failed_stages(self) -> list[StageResult]:
        return [s for s in self.stages if s.status == StageStatus.FAILED]


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, input_data: Any) -> StageResult:
        """Execute the stage and return result."""
        raise NotImplementedError

    def validate_input(self, input_data: Any) -> bool:
        """Validate input before execution. Override in subclasses."""
        return True


class DataSyncStage(PipelineStage):
    """Stage for data synchronization."""

    def __init__(self, data_sync_func: Callable[[], list[dict[str, Any]]]):
        super().__init__("data_sync")
        self._sync_func = data_sync_func

    def execute(self, input_data: Any) -> StageResult:
        try:
            result = self._sync_func()
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                output=result,
                metadata={"records_synced": len(result) if result else 0},
            )
        except Exception as e:
            logger.error(f"Data sync stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error=str(e),
            )


class FactorCalculationStage(PipelineStage):
    """Stage for factor calculation."""

    def __init__(self, factor_calc_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]):
        super().__init__("factor_calculation")
        self._calc_func = factor_calc_func

    def execute(self, input_data: Any) -> StageResult:
        try:
            if not input_data:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SKIPPED,
                    output=[],
                    metadata={"reason": "no_input_data"},
                )

            result = self._calc_func(input_data)
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                output=result,
                metadata={"factors_calculated": len(result) if result else 0},
            )
        except Exception as e:
            logger.error(f"Factor calculation stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error=str(e),
            )


class SignalScanStage(PipelineStage):
    """Stage for signal scanning."""

    def __init__(self, signal_scan_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]):
        super().__init__("signal_scan")
        self._scan_func = signal_scan_func

    def execute(self, input_data: Any) -> StageResult:
        try:
            if not input_data:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SKIPPED,
                    output=[],
                    metadata={"reason": "no_input_data"},
                )

            signals = self._scan_func(input_data)
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                output=signals,
                metadata={"signals_found": len(signals) if signals else 0},
            )
        except Exception as e:
            logger.error(f"Signal scan stage failed: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error=str(e),
            )


class Pipeline:
    """Pipeline that orchestrates multiple stages in sequence."""

    def __init__(self, name: str, stages: list[PipelineStage]):
        self.name = name
        self._stages = stages

    def add_stage(self, stage: PipelineStage) -> Pipeline:
        """Add a stage to the pipeline."""
        self._stages.append(stage)
        return self

    def execute(self, initial_input: Any = None) -> PipelineResult:
        """Execute all stages in sequence."""
        import time
        start_time = time.time()

        stage_results: list[StageResult] = []
        current_data = initial_input

        for stage in self._stages:
            if not stage.validate_input(current_data):
                result = StageResult(
                    stage_name=stage.name,
                    status=StageStatus.SKIPPED,
                    error="Input validation failed",
                )
                stage_results.append(result)
                continue

            stage_start = time.time()
            result = stage.execute(current_data)
            result.duration_ms = (time.time() - stage_start) * 1000
            stage_results.append(result)

            if result.status == StageStatus.FAILED:
                return PipelineResult(
                    pipeline_name=self.name,
                    status=PipelineStatus.FAILED,
                    stages=stage_results,
                    total_duration_ms=(time.time() - start_time) * 1000,
                    error=f"Stage '{stage.name}' failed: {result.error}",
                )

            if result.output is not None:
                current_data = result.output

        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.COMPLETED,
            stages=stage_results,
            total_duration_ms=(time.time() - start_time) * 1000,
            output=current_data,
        )


class PipelineBuilder:
    """Builder for constructing pipelines with fluent API."""

    def __init__(self, name: str):
        self._name = name
        self._stages: list[PipelineStage] = []

    def add_data_sync(self, sync_func: Callable[[], list[dict[str, Any]]]) -> PipelineBuilder:
        """Add data synchronization stage."""
        self._stages.append(DataSyncStage(sync_func))
        return self

    def add_factor_calculation(
        self,
        calc_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
    ) -> PipelineBuilder:
        """Add factor calculation stage."""
        self._stages.append(FactorCalculationStage(calc_func))
        return self

    def add_signal_scan(
        self,
        scan_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
    ) -> PipelineBuilder:
        """Add signal scan stage."""
        self._stages.append(SignalScanStage(scan_func))
        return self

    def add_custom_stage(self, stage: PipelineStage) -> PipelineBuilder:
        """Add a custom pipeline stage."""
        self._stages.append(stage)
        return self

    def build(self) -> Pipeline:
        """Build the pipeline."""
        return Pipeline(self._name, self._stages)


def create_data_pipeline(
    data_sync_func: Callable[[], list[dict[str, Any]]],
    factor_calc_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    signal_scan_func: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> Pipeline:
    """Factory function to create a complete data pipeline."""
    return (
        PipelineBuilder("data_pipeline")
        .add_data_sync(data_sync_func)
        .add_factor_calculation(factor_calc_func)
        .add_signal_scan(signal_scan_func)
        .build()
    )