from __future__ import annotations
"""Data ingestion pipeline using Chain of Responsibility."""


from abc import ABC, abstractmethod
from typing import Any, List

class PipelineStep(ABC):
    """Abstract step in the data pipeline."""

    def __init__(self, next_step: PipelineStep | None = None) -> None:
        self.next_step = next_step

    @abstractmethod
    def process(self, data: Any) -> Any:
        raise NotImplementedError

    def handle(self, data: Any) -> Any:
        processed = self.process(data)
        if self.next_step and processed is not None:
            return self.next_step.handle(processed)
        return processed

class ValidationStep(PipelineStep):
    """Step for validating market data."""
    def process(self, data: Any) -> Any:
        # e.g., filter out incomplete rows
        if "code" not in data:
            return None
        return data

class TransformationStep(PipelineStep):
    """Step for normalizing and transforming data."""
    def process(self, data: Any) -> Any:
        # e.g., cast types, normalize names
        data["price"] = float(data.get("price", 0))
        return data

class Pipeline:
    """The full data pipeline."""
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps
        # Chain them together
        for i in range(len(steps) - 1):
            steps[i].next_step = steps[i+1]
    
    def execute(self, data_list: List[dict]) -> List[dict]:
        results = []
        for item in data_list:
            res = self.steps[0].handle(item)
            if res:
                results.append(res)
        return results
