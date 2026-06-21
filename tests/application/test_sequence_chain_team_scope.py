from __future__ import annotations

from app.application.services.orchestration.sequence_chain_service import SequenceChainService
from app.domain.sequence_chain import SequenceChain


def test_list_chains_filters_by_team_id() -> None:
    svc = SequenceChainService()
    svc._by_id["a"] = SequenceChain(
        provenance_id="prov-a",
        symbol="sz000001",
        market="CN",
        team_id=10,
        visibility="team",
    )
    svc._by_id["b"] = SequenceChain(
        provenance_id="prov-b",
        symbol="sz000002",
        market="CN",
        team_id=20,
        visibility="team",
    )
    svc._by_id["c"] = SequenceChain(
        provenance_id="prov-c",
        symbol="sz000003",
        market="CN",
        team_id=99,
        visibility="public",
    )
    rows = svc.list_chains(team_id=10, limit=10)
    ids = {c.provenance_id for c in rows}
    assert "prov-a" in ids
    assert "prov-c" in ids
    assert "prov-b" not in ids


def test_set_scope_applies_to_new_chain() -> None:
    svc = SequenceChainService()
    svc.set_scope(visibility="team", team_id=7, owner_user_id=42)
    chain = svc._ensure_active_chain("sz000338", "CN", "WorkflowCompletedEvent")
    assert chain.team_id == 7
    assert chain.visibility == "team"
    assert chain.owner_user_id == 42
