from __future__ import annotations

"""TopologyLoader — load research graph structure from JSON for Swarm Designer sync."""

import json
from pathlib import Path
from typing import Any

from app.agents.research.topology_schema import ResearchGraphTopology
from app.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent / "config" / "research_graph_topology.json"
_OVERRIDE_PATH = BASE_DIR / "instance" / "research_topology" / "research_graph_topology.json"
_cache: ResearchGraphTopology | None = None


class TopologyLoader:
    """Load and validate research pipeline topology from JSON files."""

    @classmethod
    def default_path(cls) -> Path:
        return _DEFAULT_PATH

    @classmethod
    def resolve_path(cls, path: str | Path | None = None) -> Path:
        if path is not None:
            return Path(path)
        if _OVERRIDE_PATH.is_file():
            return _OVERRIDE_PATH
        return _DEFAULT_PATH

    @classmethod
    def load(cls, path: str | Path | None = None, *, use_cache: bool = True) -> ResearchGraphTopology:
        global _cache
        resolved = cls.resolve_path(path)
        if use_cache and path is None and _cache is not None:
            return _cache
        raw = json.loads(resolved.read_text(encoding="utf-8"))
        topology = ResearchGraphTopology.model_validate(raw)
        if path is None:
            _cache = topology
        logger.debug(
            "loaded research topology id=%s nodes=%d source=%s",
            topology.id,
            len(topology.nodes),
            resolved,
        )
        return topology

    @classmethod
    def save_override(cls, topology: ResearchGraphTopology | dict[str, Any]) -> Path:
        """Persist user-edited topology; takes effect on next ``load_default()``."""
        model = (
            topology
            if isinstance(topology, ResearchGraphTopology)
            else ResearchGraphTopology.model_validate(topology)
        )
        _OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = model.model_dump(mode="json", by_alias=True)
        _OVERRIDE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cls.clear_cache()
        logger.info("research topology override saved path=%s", _OVERRIDE_PATH)
        return _OVERRIDE_PATH

    @classmethod
    def load_default(cls) -> ResearchGraphTopology:
        return cls.load()

    @classmethod
    def to_swarm_descriptor(cls, path: str | Path | None = None) -> dict[str, Any]:
        """Export as Swarm Designer compatible JSON."""
        topo = cls.load(path)
        return topo.model_dump(mode="json", by_alias=True)

    @classmethod
    def clear_cache(cls) -> None:
        global _cache
        _cache = None


def get_research_graph_node_ids() -> tuple[str, ...]:
    """Node ids from default topology (single source of truth)."""
    return TopologyLoader.load_default().all_node_ids()


__all__ = ["TopologyLoader", "get_research_graph_node_ids"]
