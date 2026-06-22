"""Research Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Research Service,
which will be extracted as an independent microservice in Phase 2G.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/research/*)
"""

from __future__ import annotations

from typing import Any


class ResearchServicePort:
    """Port (interface) for research operations."""

    def get_agent_swarm_status(self, task_id: str) -> dict[str, Any]:
        """Get agent swarm status."""
        raise NotImplementedError

    def get_decision_replay(self, decision_id: str) -> dict[str, Any]:
        """Get decision replay data."""
        raise NotImplementedError

    def get_decision_theater(self, decision_id: str) -> dict[str, Any]:
        """Get decision theater visualization."""
        raise NotImplementedError

    def get_evidence_graph(self, query: str) -> dict[str, Any]:
        """Get evidence graph."""
        raise NotImplementedError

    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run simulation."""
        raise NotImplementedError

    def get_swarm_topology(self) -> dict[str, Any]:
        """Get swarm topology."""
        raise NotImplementedError

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Get workflow status."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "research",
    "version": "v1",
    "base_path": "/api/v1/research",
    "endpoints": [
        {
            "method": "GET",
            "path": "/swarm/status/{task_id}",
            "summary": "Get agent swarm status",
            "params": ["task_id (path)"],
            "response": {"status": "str", "agents": []},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/decision/replay/{decision_id}",
            "summary": "Get decision replay",
            "params": ["decision_id (path)"],
            "response": {"replay": {}},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/decision/theater/{decision_id}",
            "summary": "Get decision theater",
            "params": ["decision_id (path)"],
            "response": {"theater": {}},
            "latency_target_ms": 500,
        },
        {
            "method": "POST",
            "path": "/evidence/graph",
            "summary": "Query evidence graph",
            "params": ["query (body)"],
            "response": {"graph": {}},
            "latency_target_ms": 1000,
        },
        {
            "method": "POST",
            "path": "/simulation/run",
            "summary": "Run simulation",
            "params": ["params (body)"],
            "response": {"result": {}},
            "latency_target_ms": 5000,
        },
        {
            "method": "GET",
            "path": "/swarm/topology",
            "summary": "Get swarm topology",
            "params": [],
            "response": {"topology": {}},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/workflow/{workflow_id}",
            "summary": "Get workflow status",
            "params": ["workflow_id (path)"],
            "response": {"status": {}},
            "latency_target_ms": 200,
        },
    ],
}


def get_research_api_contract() -> dict[str, Any]:
    """Return the Research Service API contract."""
    return API_CONTRACT
