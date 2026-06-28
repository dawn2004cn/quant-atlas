from __future__ import annotations

"""Port for AI analysis report persistence."""

from abc import ABC, abstractmethod
from typing import Any


class AnalysisReportRepository(ABC):
    """Contract for storing and validating AI analysis reports."""

    @abstractmethod
    def save_report(
        self, ticker: str, user_id: int, dashboard: str, prediction: str, price: float
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_pending_reports(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_validation(self, report_id: str, score: float) -> None:
        raise NotImplementedError
