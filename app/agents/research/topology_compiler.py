from __future__ import annotations

"""Compile SwarmTopologyDescriptor into LangGraph wiring metadata."""

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.core.logger import get_logger
from app.domain.topology_schema import SwarmTopologyDescriptor, TopologyNodeKind

logger = get_logger(__name__)

# Node id → IntegratedResearchGraph executor attribute
_INTEGRATED_EXECUTOR_MAP: dict[str, str] = {
    "supervisor": "execute_supervisor",
    "department_parallel": "execute_parallel_departments",
    "evidence_routing": "execute_evidence_routing",
    "risk_manager": "execute_risk_manager",
    "synthesis": "execute_synthesis",
    "chart_vision": "execute_chart_vision",
}

# Sequential analyst roles for debate-style topologies
_ANALYST_EXECUTOR_MAP: dict[str, str] = {
    "macro": "execute_macro_analyst",
    "fundamental": "execute_fundamental_analyst",
    "technical": "execute_technical_analyst",
    "sentiment": "execute_sentiment_analyst",
    "backtest": "execute_backtest_analyst",
}


class TopologyCompiler:
    """Build a LangGraph StateGraph from a JSON topology descriptor."""

    def __init__(self, integrated_graph: Any) -> None:
        self._integrated = integrated_graph

    def compile(
        self,
        topology: SwarmTopologyDescriptor,
        *,
        state_type: Any,
        checkpointer: Any = None,
    ) -> Any:
        """Return compiled LangGraph for the given topology."""
        self.validate(topology)
        graph = StateGraph(state_type)
        node_executors = self._resolve_executors(topology)

        for node_id, fn in node_executors.items():
            graph.add_node(node_id, fn)

        if topology.entry_node:
            graph.add_edge(START, topology.entry_node)
        else:
            first = topology.nodes[0].id
            graph.add_edge(START, first)

        for edge in topology.edges:
            if edge.condition:
                logger.warning(
                    "topology_compiler: conditional edge %s→%s not fully supported, using direct edge",
                    edge.from_id,
                    edge.to_id,
                )
            graph.add_edge(edge.from_id, edge.to_id)

        exit_id = topology.exit_node or topology.nodes[-1].id
        graph.add_edge(exit_id, END)
        return graph.compile(checkpointer=checkpointer)

    def validate(self, topology: SwarmTopologyDescriptor) -> dict[str, Any]:
        """Validate topology and report compile profile."""
        order = topology.linear_execution_order()
        unsupported: list[str] = []
        for node in topology.nodes:
            if not self._has_executor(node):
                unsupported.append(node.id)
        return {
            "ok": len(unsupported) == 0,
            "execution_order": order,
            "unsupported_nodes": unsupported,
            "node_count": len(topology.nodes),
            "edge_count": len(topology.edges),
        }

    def _resolve_executors(
        self, topology: SwarmTopologyDescriptor
    ) -> dict[str, Callable[..., Any]]:
        executors: dict[str, Callable[..., Any]] = {}
        for node in topology.nodes:
            fn = self._executor_for_node(node)
            if fn is None:
                raise ValueError(f"no executor for topology node '{node.id}' ({node.kind})")
            executors[node.id] = fn
        return executors

    def _has_executor(self, node: Any) -> bool:
        return self._executor_for_node(node) is not None

    def _executor_for_node(self, node: Any) -> Callable[..., Any] | None:
        if node.id in _INTEGRATED_EXECUTOR_MAP:
            attr = _INTEGRATED_EXECUTOR_MAP[node.id]
            return getattr(self._integrated, attr)

        role = (node.agent_role or "").strip().lower()
        if role in _ANALYST_EXECUTOR_MAP:
            attr = _ANALYST_EXECUTOR_MAP[role]
            return getattr(self._integrated, attr, None)

        if node.kind == TopologyNodeKind.FILTER:
            return self._integrated.execute_evidence_routing

        if node.kind == TopologyNodeKind.DEBATE:
            role = node.agent_role or node.id

            async def _debate_node(state: Any, _role: str = role) -> dict[str, Any]:
                return await self._integrated.execute_debate_node(_role, state)

            return _debate_node

        if node.kind == TopologyNodeKind.ARBITER:
            return self._integrated.execute_arbiter_node

        if node.kind == TopologyNodeKind.VISION:
            return self._integrated.execute_chart_vision

        if node.id == "evidence_routing":
            return self._integrated.execute_evidence_routing

        return None
