"""Collaboration bounded-context DTOs (input/output contracts).

Future home for all Pydantic models consumed/produced by
``app/modules/collaboration/services/*``.
"""

from __future__ import annotations

from app.domain.team_workflow_schema import (
    TeamWorkflowDescriptor,
    TeamWorkflowEdge,
    TeamWorkflowNode,
    WorkflowNodeKind,
)

__all__ = [
    "TeamWorkflowDescriptor",
    "TeamWorkflowEdge",
    "TeamWorkflowNode",
    "WorkflowNodeKind",
]
