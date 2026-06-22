"""AI Agent Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the AI Agent Service,
which will be extracted as an independent microservice in Phase 2C.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/ai-agent/*)
"""

from __future__ import annotations

from typing import Any


class AIAgentServicePort:
    """Port (interface) for AI agent operations."""

    def analyze_stock(self, symbol: str, market: str, query: str) -> dict[str, Any]:
        """Run AI analysis on a stock."""
        raise NotImplementedError

    def get_evidence(self, symbol: str, market: str) -> dict[str, Any]:
        """Get AI evidence for a stock."""
        raise NotImplementedError

    def chat(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the AI agent chat."""
        raise NotImplementedError

    def get_committee_decision(self, topic: str) -> dict[str, Any]:
        """Get investment committee AI decision."""
        raise NotImplementedError

    def run_hedge_fund(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run AI hedge fund simulation."""
        raise NotImplementedError

    def get_fingpt_signal(self, symbol: str) -> dict[str, Any]:
        """Get FinGPT trading signal."""
        raise NotImplementedError

    def get_briefing(self, user_id: int) -> dict[str, Any]:
        """Get AI-generated daily briefing."""
        raise NotImplementedError

    def analyze_chart(self, image_data: str, symbol: str) -> dict[str, Any]:
        """Run chart vision analysis."""
        raise NotImplementedError

    def get_jarvis_response(self, query: str) -> dict[str, Any]:
        """Get Jarvis assistant response."""
        raise NotImplementedError

    def evolve_prompt(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """Evolve prompt based on feedback."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "ai_agent",
    "version": "v1",
    "base_path": "/api/v1/ai-agent",
    "endpoints": [
        {
            "method": "POST",
            "path": "/analyze",
            "summary": "Run AI stock analysis",
            "params": ["symbol (body)", "market (body)", "query (body)"],
            "response": {"analysis": "", "confidence": "float", "sources": []},
            "latency_target_ms": 2000,
        },
        {
            "method": "GET",
            "path": "/evidence/{symbol}",
            "summary": "Get AI evidence for stock",
            "params": ["symbol (path)", "market (query)"],
            "response": {"evidence": [], "trust_score": "float"},
            "latency_target_ms": 500,
        },
        {
            "method": "POST",
            "path": "/chat",
            "summary": "AI agent chat",
            "params": ["message (body)", "context (body)"],
            "response": {"response": "", "session_id": "str"},
            "latency_target_ms": 3000,
        },
        {
            "method": "GET",
            "path": "/committee/{topic}",
            "summary": "Get committee AI decision",
            "params": ["topic (path)"],
            "response": {"decision": "", "votes": [], "confidence": "float"},
            "latency_target_ms": 5000,
        },
        {
            "method": "POST",
            "path": "/hedge-fund/run",
            "summary": "Run AI hedge fund simulation",
            "params": ["params (body)"],
            "response": {"result": {}, "performance": {}},
            "latency_target_ms": 10000,
        },
        {
            "method": "GET",
            "path": "/fingpt/{symbol}",
            "summary": "Get FinGPT signal",
            "params": ["symbol (path)"],
            "response": {"signal": "str", "confidence": "float"},
            "latency_target_ms": 1000,
        },
        {
            "method": "GET",
            "path": "/briefing",
            "summary": "Get AI daily briefing",
            "params": ["user_id (query)"],
            "response": {"briefing": "", "date": "str"},
            "latency_target_ms": 2000,
        },
        {
            "method": "POST",
            "path": "/chart/analyze",
            "summary": "Chart vision analysis",
            "params": ["image_data (body)", "symbol (body)"],
            "response": {"analysis": "", "patterns": []},
            "latency_target_ms": 3000,
        },
        {
            "method": "POST",
            "path": "/jarvis",
            "summary": "Jarvis assistant query",
            "params": ["query (body)"],
            "response": {"response": "", "actions": []},
            "latency_target_ms": 2000,
        },
        {
            "method": "POST",
            "path": "/prompt/evolve",
            "summary": "Evolve prompt from feedback",
            "params": ["feedback (body)"],
            "response": {"new_prompt": "", "improvement": "float"},
            "latency_target_ms": 1000,
        },
    ],
}


def get_ai_agent_api_contract() -> dict[str, Any]:
    """Return the AI Agent Service API contract."""
    return API_CONTRACT
