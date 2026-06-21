"""Decision evidence graph routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.decision_provenance.runtime import DecisionProvenanceRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_evidence_graph_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: DecisionProvenanceRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/decision/evidence-graph/<graph_id>")
    @login_required
    def decision_evidence_graph_get(graph_id: str):
        """Fetch a decision evidence graph for DAG rendering."""
        from app.modules.system.services.ui.evidence_graph_service import (
            get_evidence_graph_service,
        )

        payload = get_evidence_graph_service().get_graph_dict(graph_id)
        if payload is None:
            raise ValidationError(f"evidence_graph_not_found: {graph_id}")
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/evidence-graph")
    @login_required
    def decision_evidence_graph_create():
        """Create a data -> capability -> reasoning -> decision graph."""
        from app.domain.evidence_graph import EvidenceNode, NodeType
        from app.modules.system.services.ui.evidence_graph_service import (
            get_evidence_graph_service,
        )

        body = request.get_json(silent=True) or {}
        subject = (body.get("subject") or body.get("symbol") or "").strip()
        if not subject:
            raise ValidationError("subject_required")
        svc = get_evidence_graph_service()
        graph = svc.create_graph(subject=subject, graph_id=body.get("graph_id"))
        nodes = {
            "data": EvidenceNode(
                id="data",
                node_type=NodeType.DATA_SOURCE,
                label="Input Data",
                summary=str(body.get("data_summary") or ""),
                payload=body.get("input_snapshot") if isinstance(body.get("input_snapshot"), dict) else {},
            ),
            "capability": EvidenceNode(
                id="capability",
                node_type=NodeType.CAPABILITY,
                label=str(body.get("capability") or "unknown_capability"),
                summary=str(body.get("capability_summary") or ""),
            ),
            "reasoning": EvidenceNode(
                id="reasoning",
                node_type=NodeType.REASONING,
                label="AI Reasoning",
                summary=str(body.get("reasoning") or ""),
            ),
            "decision": EvidenceNode(
                id="decision",
                node_type=NodeType.DECISION,
                label="Decision",
                summary=str(body.get("decision") or ""),
            ),
        }
        for node in nodes.values():
            graph.add_node(node)
        svc.chain(
            graph.graph_id,
            data_node_id="data",
            capability_node_id="capability",
            reasoning_node_id="reasoning",
            decision_node_id="decision",
        )
        return ok_response(
            data=graph.to_dict(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
