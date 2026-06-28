"""AI Agent module routes — API entrypoints for AI analysis / Jarvis / evidence."""

from __future__ import annotations

from app.presentation.api.routes_v1_ai_agent import register_ai_agent_routes
from app.presentation.api.routes_v1_ai_evidence import register_ai_evidence_routes
from app.presentation.api.routes_v1_jarvis import register_jarvis_routes

__all__ = [
    "register_ai_agent_routes",
    "register_jarvis_routes",
    "register_ai_evidence_routes",
]
