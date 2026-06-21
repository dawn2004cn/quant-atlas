"""Evidence graph service bootstrap binding."""

from __future__ import annotations

from app.modules.system.services.ui.evidence_graph_service import (
    EvidenceGraphService,
    configure_evidence_graph_service,
    get_evidence_graph_service,
)


def test_configure_evidence_graph_service_uses_bootstrap_instance():
    svc = EvidenceGraphService()
    configure_evidence_graph_service(svc)
    assert get_evidence_graph_service() is svc
