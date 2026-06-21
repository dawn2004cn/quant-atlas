"""Collaboration module routes — API entrypoints for team / blackboard / workflow."""

from __future__ import annotations

from app.presentation.api.routes_v1_collaboration import register_collaboration_routes

__all__ = ["register_collaboration_routes"]
