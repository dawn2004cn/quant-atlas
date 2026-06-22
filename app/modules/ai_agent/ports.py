"""AI Agent Service Ports (abstract interfaces).

Ports define the contracts that the AI Agent Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the AI Agent Service to be extracted as an independent microservice
in Phase 2C.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AnalysisPort(ABC):
    """Port for AI analysis operations."""

    @abstractmethod
    def analyze_stock(self, symbol: str, market: str, query: str) -> dict[str, Any]:
        """Run AI analysis on a stock."""
        raise NotImplementedError


class EvidencePort(ABC):
    """Port for AI evidence operations."""

    @abstractmethod
    def get_evidence(self, symbol: str, market: str) -> dict[str, Any]:
        """Get AI evidence for a stock."""
        raise NotImplementedError


class ChatPort(ABC):
    """Port for AI chat operations."""

    @abstractmethod
    def chat(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the AI agent chat."""
        raise NotImplementedError


class CommitteePort(ABC):
    """Port for investment committee operations."""

    @abstractmethod
    def get_decision(self, topic: str) -> dict[str, Any]:
        """Get investment committee AI decision."""
        raise NotImplementedError


class HedgeFundPort(ABC):
    """Port for AI hedge fund operations."""

    @abstractmethod
    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run AI hedge fund simulation."""
        raise NotImplementedError


class FinGPTPort(ABC):
    """Port for FinGPT operations."""

    @abstractmethod
    def get_signal(self, symbol: str) -> dict[str, Any]:
        """Get FinGPT trading signal."""
        raise NotImplementedError


class BriefingPort(ABC):
    """Port for AI briefing operations."""

    @abstractmethod
    def get_briefing(self, user_id: int) -> dict[str, Any]:
        """Get AI-generated daily briefing."""
        raise NotImplementedError


class ChartVisionPort(ABC):
    """Port for chart vision operations."""

    @abstractmethod
    def analyze_chart(self, image_data: str, symbol: str) -> dict[str, Any]:
        """Run chart vision analysis."""
        raise NotImplementedError


class JarvisPort(ABC):
    """Port for Jarvis assistant operations."""

    @abstractmethod
    def query(self, query: str) -> dict[str, Any]:
        """Get Jarvis assistant response."""
        raise NotImplementedError


class PromptEvolutionPort(ABC):
    """Port for prompt evolution operations."""

    @abstractmethod
    def evolve(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """Evolve prompt based on feedback."""
        raise NotImplementedError


class ResearchPort(ABC):
    """Port for AI research operations."""

    @abstractmethod
    def research(self, query: str, depth: str = "standard") -> dict[str, Any]:
        """Run AI research on a topic."""
        raise NotImplementedError
