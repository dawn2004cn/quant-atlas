"""API v1: decision provenance dispatcher."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.decision_provenance import (
    DecisionProvenanceRuntime,
    register_decision_lifecycle_routes,
    register_evidence_graph_routes,
    register_sequence_chain_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="decision_provenance", context="system", description="Decision provenance and evidence graphs")
def register_decision_provenance_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register decision provenance and evidence graph routes."""
    runtime = DecisionProvenanceRuntime(ctx=ctx)
    register_sequence_chain_routes(blueprint, ctx, runtime=runtime)
    register_evidence_graph_routes(blueprint, ctx, runtime=runtime)
    register_decision_lifecycle_routes(blueprint, ctx, runtime=runtime)
