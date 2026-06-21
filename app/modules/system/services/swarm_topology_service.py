from __future__ import annotations
"""Swarm topology CRUD and compile validation for Swarm Designer."""

import re
import uuid
from typing import Any

from app.agents.research.topology_compiler import TopologyCompiler
from app.core.logger import get_logger
from app.domain.swarm_topology_presets import PRESET_REGISTRY, list_preset_summaries
from app.domain.topology_schema import SwarmTopologyDescriptor
from app.infrastructure.repositories.file_swarm_topology_repository import (
    FileSwarmTopologyRepository,
)

logger = get_logger(__name__)


class SwarmTopologyService:
    """Manage JSON swarm graphs and validate compile readiness."""

    def __init__(self, *, repository: FileSwarmTopologyRepository | None = None) -> None:
        self._repo = repository or FileSwarmTopologyRepository()

    def list_presets(self) -> dict[str, Any]:
        presets = list_preset_summaries()
        presets.append(
            {
                "id": "research_default",
                "name": "研究图谱（TopologyLoader）",
                "description": "与 graph.py 运行时一致的 research_graph_topology.json",
            }
        )
        return {"ok": True, "presets": presets}

    def get_research_graph_topology(self) -> dict[str, Any]:
        """Export live research graph JSON for Swarm Designer."""
        try:
            from app.agents.research.topology_loader import TopologyLoader

            path = TopologyLoader.resolve_path()
            topo = TopologyLoader.load_default()
            return {
                "ok": True,
                "topology": topo.model_dump(mode="json", by_alias=True),
                "source": str(path),
                "editable": True,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def save_research_graph_topology(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and persist research graph override (React Flow editor)."""
        try:
            from app.agents.research.topology_loader import TopologyLoader
            from app.agents.research.topology_schema import ResearchGraphTopology

            topo = ResearchGraphTopology.model_validate(payload)
            saved = TopologyLoader.save_override(topo)
            validation = self.validate_topology(
                SwarmTopologyDescriptor.model_validate(
                    {
                        "schema_version": topo.schema_version,
                        "id": topo.id,
                        "name": topo.name,
                        "description": topo.description,
                        "nodes": [n.model_dump() for n in topo.nodes],
                        "edges": [
                            {"from": e.from_id, "to": e.to_id} for e in topo.edges
                        ],
                        "entry_node": topo.entry_node,
                        "exit_node": topo.exit_node,
                    }
                )
            )
            return {
                "ok": True,
                "saved_to": str(saved),
                "topology": topo.model_dump(mode="json", by_alias=True),
                "validation": validation,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_preset(self, preset_id: str) -> dict[str, Any]:
        if preset_id == "research_default":
            return self.get_research_graph_topology()
        topo = PRESET_REGISTRY.get(preset_id)
        if topo is None:
            return {"ok": False, "error": "preset_not_found"}
        return {"ok": True, "topology": topo.model_dump()}

    def list_user_topologies(self, user_id: int) -> dict[str, Any]:
        return {"ok": True, "items": self._repo.list_for_user(user_id)}

    def get_user_topology(self, user_id: int, topology_id: str) -> dict[str, Any]:
        topo = self._repo.get(user_id, topology_id)
        if topo is None:
            return {"ok": False, "error": "topology_not_found"}
        return {"ok": True, "topology": topo.model_dump()}

    def save_user_topology(
        self,
        user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw_id = (payload.get("id") or "").strip() or f"custom-{uuid.uuid4().hex[:8]}"
        clean_id = self._slugify(raw_id)
        payload["id"] = clean_id
        if not payload.get("name"):
            payload["name"] = clean_id
        try:
            topo = SwarmTopologyDescriptor.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": "invalid_topology", "details": str(exc)}
        saved = self._repo.save(user_id, topo)
        validation = self.validate_topology(saved)
        return {
            "ok": True,
            "topology": saved.model_dump(),
            "validation": validation,
        }

    def validate_topology(self, topology: SwarmTopologyDescriptor) -> dict[str, Any]:
        try:
            from unittest.mock import MagicMock

            from app.agents.research.integrated_graph import IntegratedResearchGraph

            compiler = TopologyCompiler(IntegratedResearchGraph(MagicMock()))
            return compiler.validate(topology)
        except Exception as exc:  # noqa: BLE001
            logger.debug("swarm_topology validate: %s", exc)
            return {"ok": False, "error": str(exc)}

    def designer_blocks(self) -> dict[str, Any]:
        """Palette of draggable blocks for Swarm Designer UI."""
        return {
            "ok": True,
            "blocks": [
                {"kind": "supervisor", "label": "编排者", "agent_role": ""},
                {"kind": "agent", "label": "宏观分析", "agent_role": "macro"},
                {"kind": "agent", "label": "基本面", "agent_role": "fundamental"},
                {"kind": "agent", "label": "技术面", "agent_role": "technical"},
                {"kind": "agent", "label": "情绪面", "agent_role": "sentiment"},
                {"kind": "agent", "label": "回测优化", "agent_role": "backtest"},
                {"kind": "parallel_group", "label": "并行分析组", "agent_role": ""},
                {"kind": "filter", "label": "证据过滤", "agent_role": ""},
                {"kind": "debate", "label": "辩论节点", "agent_role": "bull"},
                {"kind": "arbiter", "label": "最终仲裁", "agent_role": ""},
                {"kind": "agent", "label": "风险管理", "agent_role": "risk_manager"},
                {"kind": "synthesis", "label": "综合决策", "agent_role": ""},
            ],
        }

    def generate_topology(self, regime: str, *, symbol: str = "") -> dict[str, Any]:
        from app.modules.system.services.topology_generator import TopologyGenerator

        gen = TopologyGenerator()
        topo = gen.generate_from_regime(regime, symbol=symbol)
        return {"ok": True, "topology": topo.model_dump(mode="json"), "regime": regime}

    def propose_agents(self, event_context: dict[str, Any]) -> dict[str, Any]:
        from app.modules.system.services.topology_generator import TopologyGenerator

        gen = TopologyGenerator()
        return {"ok": True, **gen.propose_new_agent(event_context)}

    def list_topology_templates(self) -> dict[str, Any]:
        from app.modules.system.services.topology_generator import TopologyGenerator

        gen = TopologyGenerator()
        return {"ok": True, "templates": gen.list_templates(), "regime_presets": gen.list_regime_presets()}

    @staticmethod
    def _slugify(value: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", (value or "topology").strip().lower())
        return s.strip("-")[:48] or "topology"
