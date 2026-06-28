from __future__ import annotations

"""Built-in swarm topology presets for Swarm Designer."""

from app.domain.topology_schema import (
    SwarmTopologyDescriptor,
    TopologyEdge,
    TopologyNode,
    TopologyNodeKind,
)


def preset_integrated_parallel() -> SwarmTopologyDescriptor:
    """Default integrated graph: parallel departments → filter → risk → synthesis."""
    nodes = [
        TopologyNode(id="supervisor", kind=TopologyNodeKind.SUPERVISOR, label="编排者"),
        TopologyNode(
            id="department_parallel",
            kind=TopologyNodeKind.PARALLEL_GROUP,
            label="六分析师并行",
            config={"roles": ["macro", "fundamental", "technical", "sentiment", "backtest"]},
        ),
        TopologyNode(id="evidence_routing", kind=TopologyNodeKind.FILTER, label="证据路由/早停"),
        TopologyNode(
            id="risk_manager",
            kind=TopologyNodeKind.AGENT,
            agent_role="risk_manager",
            label="风险管理",
        ),
        TopologyNode(id="synthesis", kind=TopologyNodeKind.SYNTHESIS, label="综合决策"),
    ]
    edges = [
        TopologyEdge(**{"from": "supervisor", "to": "department_parallel"}),
        TopologyEdge(**{"from": "department_parallel", "to": "evidence_routing"}),
        TopologyEdge(**{"from": "evidence_routing", "to": "risk_manager"}),
        TopologyEdge(**{"from": "risk_manager", "to": "synthesis"}),
    ]
    return SwarmTopologyDescriptor(
        id="integrated_parallel",
        name="集成并行流水线",
        description="Supervisor → 六分析师并行 → 证据过滤 → 风控 → 综合决策",
        nodes=nodes,
        edges=edges,
        entry_node="supervisor",
        exit_node="synthesis",
    )


def preset_debate_pipeline() -> SwarmTopologyDescriptor:
    """Industry-style chain: Macro → Filter → Bull/Bear Debate → Arbiter."""
    nodes = [
        TopologyNode(id="supervisor", kind=TopologyNodeKind.SUPERVISOR, label="编排者"),
        TopologyNode(
            id="macro_analyst",
            kind=TopologyNodeKind.AGENT,
            agent_role="macro",
            label="宏观分析",
        ),
        TopologyNode(id="evidence_filter", kind=TopologyNodeKind.FILTER, label="证据过滤"),
        TopologyNode(
            id="fundamental_analyst",
            kind=TopologyNodeKind.AGENT,
            agent_role="fundamental",
            label="基本面",
        ),
        TopologyNode(
            id="technical_analyst",
            kind=TopologyNodeKind.AGENT,
            agent_role="technical",
            label="技术面",
        ),
        TopologyNode(
            id="bull_debate",
            kind=TopologyNodeKind.DEBATE,
            agent_role="bull",
            label="多头辩论",
            config={"rounds": 2},
        ),
        TopologyNode(
            id="bear_debate",
            kind=TopologyNodeKind.DEBATE,
            agent_role="bear",
            label="空头辩论",
            config={"rounds": 2},
        ),
        TopologyNode(
            id="final_arbiter",
            kind=TopologyNodeKind.ARBITER,
            label="最终仲裁",
        ),
        TopologyNode(id="synthesis", kind=TopologyNodeKind.SYNTHESIS, label="决策输出"),
    ]
    edges = [
        TopologyEdge(**{"from": "supervisor", "to": "macro_analyst"}),
        TopologyEdge(**{"from": "macro_analyst", "to": "evidence_filter"}),
        TopologyEdge(**{"from": "evidence_filter", "to": "fundamental_analyst"}),
        TopologyEdge(**{"from": "fundamental_analyst", "to": "technical_analyst"}),
        TopologyEdge(**{"from": "technical_analyst", "to": "bull_debate"}),
        TopologyEdge(**{"from": "bull_debate", "to": "bear_debate"}),
        TopologyEdge(**{"from": "bear_debate", "to": "final_arbiter"}),
        TopologyEdge(**{"from": "final_arbiter", "to": "synthesis"}),
    ]
    return SwarmTopologyDescriptor(
        id="debate_pipeline",
        name="辩论仲裁流水线",
        description="Macro → Filter → 基本面/技术 → Bull/Bear 辩论 → Final Arbiter",
        nodes=nodes,
        edges=edges,
        entry_node="supervisor",
        exit_node="synthesis",
    )


PRESET_REGISTRY: dict[str, SwarmTopologyDescriptor] = {
    "integrated_parallel": preset_integrated_parallel(),
    "debate_pipeline": preset_debate_pipeline(),
}


def list_preset_summaries() -> list[dict[str, str]]:
    return [
        {
            "id": topo.id,
            "name": topo.name,
            "description": topo.description,
            "node_count": str(len(topo.nodes)),
        }
        for topo in PRESET_REGISTRY.values()
    ]
