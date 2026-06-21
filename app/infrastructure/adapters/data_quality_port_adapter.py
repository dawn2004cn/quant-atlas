from __future__ import annotations
"""Infrastructure adapter for ``DataQualityPort``."""

from typing import Any

from app.domain.ports.data_quality_port import DataQualityPort
from app.infrastructure.agent.data.quality_checker import QualityChecker


class DataQualityPortAdapter(DataQualityPort):
    def __init__(self) -> None:
        self._checker = QualityChecker()

    def validate(self, data: Any) -> list[Any]:
        return self._checker.validate(data)
