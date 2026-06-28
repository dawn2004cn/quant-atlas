from __future__ import annotations

"""Pipeline design pattern for data processing.

Implements Reader -> Validator -> Transformer -> Writer pattern
for standardized data processing workflows.
"""


from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')
R = TypeVar('R')
V = TypeVar('V')
W = TypeVar('W')


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processed_count: int = 0
    elapsed_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class PipelineStage(ABC, Generic[T]):
    """Base class for pipeline stages."""

    @abstractmethod
    def process(self, data: T) -> T:
        """Process data through this stage."""
        pass

    def validate(self, data: T) -> bool:
        """Validate data can be processed."""
        return True


class Reader(PipelineStage[dict]):
    """Data reader stage."""

    def __init__(self, source: str, read_fn: Callable[[], list[dict]]):
        self.source = source
        self.read_fn = read_fn

    def process(self, data: dict | None = None) -> list[dict]:
        """Read data from source."""
        logger.info(f"Reading data from {self.source}")
        try:
            return self.read_fn()
        except Exception as e:
            logger.error(f"Error reading from {self.source}: {e}")
            return []


class Validator(PipelineStage[list[dict]]):
    """Data validator stage."""

    def __init__(self, validators: list[Callable[[dict], bool]]):
        self.validators = validators

    def process(self, data: list[dict]) -> list[dict]:
        """Validate data records."""
        valid_records = []
        invalid_count = 0

        for record in data:
            is_valid = all(validator(record) for validator in self.validators)
            if is_valid:
                valid_records.append(record)
            else:
                invalid_count += 1

        if invalid_count > 0:
            logger.warning(f"Rejected {invalid_count} invalid records")

        return valid_records


class Transformer(PipelineStage[list[dict]]):
    """Data transformer stage."""

    def __init__(self, transformers: list[Callable[[dict], dict]]):
        self.transformers = transformers

    def process(self, data: list[dict]) -> list[dict]:
        """Transform data records."""
        transformed = []

        for record in data:
            try:
                result = record
                for transformer in self.transformers:
                    result = transformer(result)
                transformed.append(result)
            except Exception as e:
                logger.error(f"Error transforming record: {e}")

        return transformed


class Writer(PipelineStage[list[dict]]):
    """Data writer stage."""

    def __init__(self, destination: str, write_fn: Callable[[list[dict]], bool]):
        self.destination = destination
        self.write_fn = write_fn

    def process(self, data: list[dict]) -> dict:
        """Write data to destination."""
        logger.info(f"Writing {len(data)} records to {self.destination}")
        try:
            success = self.write_fn(data)
            return {"success": success, "written_count": len(data)}
        except Exception as e:
            logger.error(f"Error writing to {self.destination}: {e}")
            return {"success": False, "error": str(e)}


class DataPipeline:
    """Complete data pipeline."""

    def __init__(
        self,
        name: str,
        reader: Reader | None = None,
        validators: list[Validator] | None = None,
        transformers: list[Transformer] | None = None,
        writers: list[Writer] | None = None,
    ):
        self.name = name
        self.reader = reader
        self.validators = validators or []
        self.transformers = transformers or []
        self.writers = writers or []
        logger.info(f"Pipeline '{name}' initialized")

    def execute(self) -> PipelineResult:
        """Execute the complete pipeline."""
        start_time = datetime.now()
        errors = []
        warnings = []

        try:
            data = []
            if self.reader:
                data = self.reader.process()
                if not data:
                    warnings.append("No data read from source")

            for validator in self.validators:
                prev_count = len(data)
                data = validator.process(data)
                removed = prev_count - len(data)
                if removed > 0:
                    warnings.append(f"Validator removed {removed} records")

            for transformer in self.transformers:
                data = transformer.process(data)

            for writer in self.writer_process(data):
                if not writer.get("success", False):
                    errors.append(writer.get("error", "Unknown error"))

            elapsed = (datetime.now() - start_time).total_seconds()

            return PipelineResult(
                success=len(errors) == 0,
                data=data,
                errors=errors,
                warnings=warnings,
                processed_count=len(data),
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            elapsed = (datetime.now() - start_time).total_seconds()
            return PipelineResult(
                success=False,
                errors=[str(e)],
                elapsed_seconds=elapsed,
            )

    def writer_process(self, data: list[dict]) -> list[dict]:
        """Process writers."""
        results = []
        for writer in self.writers:
            results.append(writer.process(data))
        return results


class DataQualityGate:
    """Data quality gate for pipeline."""

    @staticmethod
    def check_required_fields(record: dict, required_fields: list[str]) -> bool:
        """Check if record has required fields."""
        return all(field in record and record[field] is not None for field in required_fields)

    @staticmethod
    def check_value_range(record: dict, field: str, min_val: float, max_val: float) -> bool:
        """Check if value is within range."""
        if field not in record or record[field] is None:
            return True
        try:
            value = float(record[field])
            return min_val <= value <= max_val
        except (ValueError, TypeError):
            return False

    @staticmethod
    def check_not_null(record: dict, fields: list[str]) -> bool:
        """Check fields are not null."""
        return all(record.get(field) is not None for field in fields)

    @staticmethod
    def check_enum(record: dict, field: str, allowed_values: list[str]) -> bool:
        """Check value is in allowed enum."""
        if field not in record:
            return True
        return record[field] in allowed_values


class PipelineBuilder:
    """Builder for creating pipelines."""

    def __init__(self, name: str):
        self.name = name
        self._reader: Reader | None = None
        self._validators: list[Validator] = []
        self._transformers: list[Transformer] = []
        self._writers: list[Writer] = []

    def with_reader(self, source: str, read_fn: Callable[[], list[dict]]) -> PipelineBuilder:
        """Add reader stage."""
        self._reader = Reader(source, read_fn)
        return self

    def with_validator(self, validators: list[Callable[[dict], bool]]) -> PipelineBuilder:
        """Add validator stage."""
        self._validators.append(Validator(validators))
        return self

    def with_transformer(self, transformers: list[Callable[[dict], dict]]) -> PipelineBuilder:
        """Add transformer stage."""
        self._transformers.append(Transformer(transformers))
        return self

    def with_writer(self, destination: str, write_fn: Callable[[list[dict]], bool]) -> PipelineBuilder:
        """Add writer stage."""
        self._writers.append(Writer(destination, write_fn))
        return self

    def build(self) -> DataPipeline:
        """Build the pipeline."""
        return DataPipeline(
            name=self.name,
            reader=self._reader,
            validators=self._validators,
            transformers=self._transformers,
            writers=self._writers,
        )


__all__ = [
    "PipelineStage",
    "Reader",
    "Validator",
    "Transformer",
    "Writer",
    "DataPipeline",
    "DataQualityGate",
    "PipelineBuilder",
    "PipelineResult",
]
