from __future__ import annotations
"""Pipeline abstraction for data processing flows."""


from typing import Any, Generic, TypeVar
from collections.abc import Callable


from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class PipelineStage(Generic[T, R]):
    """A single stage in a data pipeline."""

    def __init__(self, name: str, processor: Callable[[T], R]):
        self.name = name
        self.processor = processor

    def execute(self, input_data: T) -> R:
        """Execute this stage."""
        try:
            return self.processor(input_data)
        except Exception as e:
            logger.error("Pipeline stage '%s' failed: %s", self.name, e)
            raise


class Pipeline(Generic[T]):
    """Data processing pipeline with multiple stages."""

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self._stages: list[PipelineStage] = []

    def add_stage(self, name: str, processor: Callable) -> Pipeline:
        """Add a processing stage."""
        self._stages.append(PipelineStage(name, processor))
        return self

    def execute(self, input_data: Any) -> Any:
        """Execute all stages in sequence."""
        result = input_data
        for stage in self._stages:
            logger.debug("Executing stage: %s", stage.name)
            result = stage.execute(result)
        return result


class DataPipeline(Pipeline):
    """Specialized pipeline for market data."""

    def __init__(self, name: str = "data_pipeline"):
        super().__init__(name)
        self._validators: list[Callable] = []
        self._transformers: list[Callable] = []

    def add_validator(self, validator: Callable[[Any], bool]) -> DataPipeline:
        """Add data validation step."""
        self._validators.append(validator)
        return self

    def add_transformer(self, transformer: Callable) -> DataPipeline:
        """Add data transformation step."""
        self._transformers.append(transformer)
        return self

    def process(self, data: Any) -> tuple[bool, Any]:
        """Process data through validation and transformation."""
        for validator in self._validators:
            try:
                if not validator(data):
                    logger.warning("Data validation failed in %s", self.name)
                    return False, data
            except Exception as e:
                logger.warning("Validator error: %s", e)
                return False, data

        for transformer in self._transformers:
            try:
                data = transformer(data)
            except Exception as e:
                logger.warning("Transformer error: %s", e)
                return False, data

        return True, data


def reader_stage(name: str, fetch_func: Callable) -> PipelineStage:
    """Create a reader stage."""
    return PipelineStage(f"reader:{name}", fetch_func)


def validator_stage(name: str, validate_func: Callable[[Any], bool]) -> PipelineStage:
    """Create a validator stage."""
    return PipelineStage(f"validator:{name}", lambda data: (validate_func(data), data)[1] if validate_func(data) else None)


def transformer_stage(name: str, transform_func: Callable) -> PipelineStage:
    """Create a transformer stage."""
    return PipelineStage(f"transformer:{name}", transform_func)


def writer_stage(name: str, write_func: Callable) -> PipelineStage:
    """Create a writer stage."""
    return PipelineStage(f"writer:{name}", write_func)
