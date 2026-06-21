"""Execution module routes — API entrypoints for borderless / self-healing execution."""

from __future__ import annotations

from app.presentation.api.routes_v1_execution import register_execution_routes
from app.presentation.api.routes_v1_self_healing_execution import register_self_healing_execution_routes

__all__ = [
    "register_execution_routes",
    "register_self_healing_execution_routes",
]
