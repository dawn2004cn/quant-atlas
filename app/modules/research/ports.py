"""Research Service Ports (abstract interfaces).

Ports define the contracts that the Research Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the Research Service to be extracted as an independent microservice
in Phase 2G.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentSwarmPort(ABC):
    """Port for agent swarm operations."""

    @abstractmethod
    def get_status(self, task_id: str) -> dict[str, Any]:
        """Get agent swarm status."""
        raise NotImplementedError


class DecisionReplayPort(ABC):
    """Port for decision replay operations."""

    @abstractmethod
    def get_replay(self, decision_id: str) -> dict[str, Any]:
        """Get decision replay data."""
        raise NotImplementedError


class DecisionTheaterPort(ABC):
    """Port for decision theater operations."""

    @abstractmethod
    def get_theater(self, decision_id: str) -> dict[str, Any]:
        """Get decision theater visualization."""
        raise NotImplementedError


class EvidenceGraphPort(ABC):
    """Port for evidence graph operations."""

    @abstractmethod
    def query(self, query: str) -> dict[str, Any]:
        """Query evidence graph."""
        raise NotImplementedError


class SimulationPort(ABC):
    """Port for simulation operations."""

    @abstractmethod
    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run simulation."""
        raise NotImplementedError


class SwarmTopologyPort(ABC):
    """Port for swarm topology operations."""

    @abstractmethod
    def get_topology(self) -> dict[str, Any]:
        """Get swarm topology."""
        raise NotImplementedError


class WorkflowPort(ABC):
    """Port for workflow operations."""

    @abstractmethod
    def get_status(self, workflow_id: str) -> dict[str, Any]:
        """Get workflow status."""
        raise NotImplementedError
