from __future__ import annotations

import pytest

from app.domain.swarm_topology_presets import PRESET_REGISTRY, preset_integrated_parallel
from app.domain.topology_schema import SwarmTopologyDescriptor


def test_integrated_preset_is_valid_dag() -> None:
    topo = preset_integrated_parallel()
    order = topo.linear_execution_order()
    assert order[0] == "supervisor"
    assert order[-1] == "synthesis"
    assert len(order) == len(topo.nodes)


def test_preset_registry_contains_debate_pipeline() -> None:
    assert "debate_pipeline" in PRESET_REGISTRY
    debate = PRESET_REGISTRY["debate_pipeline"]
    assert any(n.kind.value == "debate" for n in debate.nodes)


def test_invalid_entry_node_raises() -> None:
    topo = preset_integrated_parallel()
    data = topo.model_dump()
    data["entry_node"] = "missing"
    with pytest.raises(Exception):
        SwarmTopologyDescriptor.model_validate(data)
