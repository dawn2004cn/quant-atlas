from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.research.topology_loader import TopologyLoader


def test_topology_save_override_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    override = tmp_path / "research_graph_topology.json"
    monkeypatch.setattr(
        "app.agents.research.topology_loader._OVERRIDE_PATH",
        override,
    )
    TopologyLoader.clear_cache()
    original = TopologyLoader.load(TopologyLoader.default_path(), use_cache=False)
    payload = original.model_dump(mode="json", by_alias=True)
    payload["name"] = "测试覆盖拓扑"
    saved = TopologyLoader.save_override(payload)
    assert saved == override
    TopologyLoader.clear_cache()
    loaded = TopologyLoader.load_default()
    assert loaded.name == "测试覆盖拓扑"
    TopologyLoader.clear_cache()
