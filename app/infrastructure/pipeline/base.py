from __future__ import annotations

"""Pipeline architecture for data processing."""

from abc import ABC, abstractmethod
from typing import Any


class DataProcessor(ABC):
    """Abstract base class for a pipeline processing step."""

    def __init__(self, next_processor: DataProcessor | None = None):
        self.next_processor = next_processor

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process the data."""
        pass

    def handle(self, data: Any) -> Any:
        result = self.process(data)
        if result is not None and self.next_processor:
            return self.next_processor.handle(result)
        return result

class Pipeline:
    """Orchestrator for a chain of processors."""
    def __init__(self, processors: list[DataProcessor]):
        self.chain = processors[0]
        for i in range(len(processors) - 1):
            processors[i].next_processor = processors[i+1]

    def execute(self, data: Any) -> Any:
        return self.chain.handle(data)
