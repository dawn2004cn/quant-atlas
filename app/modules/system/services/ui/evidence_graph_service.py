from __future__ import annotations
"""Evidence Graph Service — builds provenance graphs from capability & workflow execution."""


import uuid
from typing import Any

from app.core.event_bus import (
    CapabilityExecutedEvent,
    WorkflowCompletedEvent,
    on_event,
)
from app.core.registry import register_service
from app.domain.evidence_graph import (
    EvidenceGraph,
    EvidenceNode,
    EdgeLabel,
    NodeType,
)


@register_service(name="evidence_graph_service")
class EvidenceGraphService:
    """Builds and serves provenance graphs.

    Automatically subscribes to ``CapabilityExecutedEvent`` and
    ``WorkflowCompletedEvent`` on the global event bus to record
    evidence nodes with zero coupling.
    """

    def __init__(self) -> None:
        self._graphs: dict[str, EvidenceGraph] = {}

    # ── public API ───────────────────────────────────────────────────────

    def get_graph(self, graph_id: str) -> EvidenceGraph | None:
        return self._graphs.get(graph_id)

    def get_graph_dict(self, graph_id: str) -> dict[str, Any] | None:
        g = self.get_graph(graph_id)
        return g.to_dict() if g else None

    def create_graph(self, subject: str, graph_id: str | None = None) -> EvidenceGraph:
        gid = graph_id or f"eg_{uuid.uuid4().hex[:12]}"
        g = EvidenceGraph(graph_id=gid, subject=subject)
        self._graphs[gid] = g
        return g

    def add_node(self, graph_id: str, node: EvidenceNode) -> bool:
        g = self._graphs.get(graph_id)
        if g is None:
            return False
        g.add_node(node)
        return True

    def add_edge(
        self, graph_id: str, source_id: str, target_id: str,
        label: EdgeLabel = EdgeLabel.FEEDS_INTO,
        **metadata: Any,
    ) -> bool:
        g = self._graphs.get(graph_id)
        if g is None:
            return False
        g.link(source_id, target_id, label, **metadata)
        return True

    # ── event-driven capture ─────────────────────────────────────────────

    def capture_capability_execution(
        self,
        capability_name: str,
        success: bool,
        duration_ms: float,
        *,
        graph_id: str | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Record a capability execution as a graph node.

        Returns the node ID if a matching graph was found.
        """
        gid = graph_id
        if not gid:
            return None
        g = self._graphs.get(gid)
        if g is None:
            return None
        nid = f"cap_{capability_name}_{uuid.uuid4().hex[:8]}"
        node = EvidenceNode(
            id=nid,
            node_type=NodeType.CAPABILITY,
            label=capability_name,
            summary=f"{'OK' if success else 'FAIL'} in {duration_ms:.0f}ms",
            payload={"success": success, "duration_ms": duration_ms, **kwargs},
        )
        g.add_node(node)
        return nid

    def capture_workflow_completion(
        self,
        workflow_id: str,
        workflow_type: str,
        state: str,
        evidence_count: int = 0,
    ) -> str | None:
        """Record a workflow completion as a graph node."""
        nid = f"wf_{workflow_id}_{uuid.uuid4().hex[:8]}"
        node = EvidenceNode(
            id=nid,
            node_type=NodeType.WORKFLOW,
            label=f"{workflow_type}:{workflow_id[:12]}",
            summary=f"State: {state}, evidence: {evidence_count}",
            payload={"workflow_id": workflow_id, "workflow_type": workflow_type, "state": state, "evidence_count": evidence_count},
        )
        # Store in a graph keyed by workflow_id for easy lookup
        g = self._graphs.get(workflow_id)
        if g is None:
            g = self.create_graph(subject=f"Workflow {workflow_id}", graph_id=workflow_id)
        g.add_node(node)
        return nid

    # ── helpers for building chain ───────────────────────────────────────

    def chain(
        self,
        graph_id: str,
        *,
        data_node_id: str | None = None,
        capability_node_id: str | None = None,
        reasoning_node_id: str | None = None,
        decision_node_id: str | None = None,
    ) -> None:
        """Link an ordered chain: data → capability → reasoning → decision."""
        pairs = [
            (data_node_id, capability_node_id),
            (capability_node_id, reasoning_node_id),
            (reasoning_node_id, decision_node_id),
        ]
        for src, tgt in pairs:
            if src and tgt:
                self.add_edge(graph_id, src, tgt, EdgeLabel.FEEDS_INTO)


# ── global singleton ─────────────────────────────────────────────────────

_evidence_graph_service: EvidenceGraphService | None = None


def configure_evidence_graph_service(svc: EvidenceGraphService | None) -> None:
    """Bind bootstrap-wired instance for event handlers and route getters."""
    global _evidence_graph_service
    if svc is not None:
        _evidence_graph_service = svc


def get_evidence_graph_service() -> EvidenceGraphService:
    global _evidence_graph_service
    if _evidence_graph_service is None:
        _evidence_graph_service = EvidenceGraphService()
    return _evidence_graph_service


# ── auto-subscription ────────────────────────────────────────────────────


@on_event(CapabilityExecutedEvent)
def _on_capability_executed(event: CapabilityExecutedEvent) -> None:
    svc = get_evidence_graph_service()
    svc.capture_capability_execution(
        event.capability_name,
        event.success,
        event.duration_ms,
    )


@on_event(WorkflowCompletedEvent)
def _on_workflow_completed(event: WorkflowCompletedEvent) -> None:
    svc = get_evidence_graph_service()
    svc.capture_workflow_completion(
        event.workflow_id,
        event.workflow_type,
        event.state,
        event.evidence_count,
    )
