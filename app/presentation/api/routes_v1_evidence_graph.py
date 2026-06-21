from __future__ import annotations
"""API v1: Evidence graph routes."""


from flask import Blueprint
from flask_login import login_required

from ...application.errors import ValidationError
from app.modules.system.services.ui.evidence_graph_service import get_evidence_graph_service
from .common import ok_resource
from .v1_context import ApiV1Context
from app.core.registry import register_routes


@register_routes(name="evidence_graph", context="research", description="Evidence graph routes")
def register_evidence_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/evidence/graph/<graph_id>")
    @login_required
    def evidence_graph(graph_id: str):
        svc = get_evidence_graph_service()
        graph = svc.get_graph_dict(graph_id)
        if graph is None:
            raise ValidationError(f"evidence_graph_not_found: {graph_id}")
        return ok_resource(
            resource=graph,
            resource_key="evidence_graph",
            enable_legacy_alias=legacy,
        )
