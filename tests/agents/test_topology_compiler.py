from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.research.integrated_graph import IntegratedResearchGraph, resolve_topology
from app.agents.research.topology_compiler import TopologyCompiler
from app.domain.swarm_topology_presets import preset_integrated_parallel


def test_compiler_validates_integrated_preset() -> None:
    topo = preset_integrated_parallel()
    compiler = TopologyCompiler(IntegratedResearchGraph(MagicMock()))
    result = compiler.validate(topo)
    assert result["ok"] is True
    assert result["unsupported_nodes"] == []


def test_resolve_topology_preset_id() -> None:
    topo = resolve_topology("integrated_parallel")
    assert topo.id == "integrated_parallel"
