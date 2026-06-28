from __future__ import annotations
"""TopologyGenerator — dynamic agent cloning & topology self-assembly (9.0 Swarm Morphing)."""

import uuid
from typing import Any

from app.core.logger import get_logger
from app.domain.topology_schema import (
    SwarmTopologyDescriptor,
    TopologyEdge,
    TopologyNode,
    TopologyNodeKind,
)

logger = get_logger(__name__)

_AGENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "macro_analyst": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "macro_analyst",
        "label": "宏观分析",
        "config": {"focus": "macro_economy", "data_sources": ["cpi", "gdp", "rates"]},
    },
    "fundamental_analyst": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "fundamental_analyst",
        "label": "基本面",
        "config": {"focus": "financials", "data_sources": ["income", "balance_sheet", "cashflow"]},
    },
    "technical_analyst": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "technical_analyst",
        "label": "技术面",
        "config": {"focus": "price_action", "indicators": ["ma", "rsi", "macd", "boll"]},
    },
    "sentiment_analyst": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "sentiment_analyst",
        "label": "情绪面",
        "config": {"focus": "sentiment", "data_sources": ["news", "social", "options_flow"]},
    },
    "backtest_optimizer": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "backtest_optimizer",
        "label": "回测优化",
        "config": {"focus": "backtest", "period": "1y", "strategies": ["momentum", "mean_reversion"]},
    },
    "risk_manager": {
        "kind": TopologyNodeKind.AGENT,
        "agent_role": "risk_manager",
        "label": "风险管理",
        "config": {"focus": "risk", "metrics": ["var", "drawdown", "correlation"]},
    },
    "bull": {
        "kind": TopologyNodeKind.DEBATE,
        "agent_role": "bull",
        "label": "多头辩论",
        "config": {"stance": "bullish", "rounds": 3},
    },
    "bear": {
        "kind": TopologyNodeKind.DEBATE,
        "agent_role": "bear",
        "label": "空头辩论",
        "config": {"stance": "bearish", "rounds": 3},
    },
    "chart_vision": {
        "kind": TopologyNodeKind.VISION,
        "agent_role": "chart_vision",
        "label": "图形识别",
        "config": {"focus": "visual_patterns", "indicators": ["ma5", "ma20", "ma60"], "days": 120},
    },
}

_REGIME_TOPOLOGY_PRESETS: dict[str, dict[str, Any]] = {
    "high_volatility": {
        "name": "高波动防御拓扑",
        "description": "强化风险管理和情绪分析，简化辩论流程",
        "nodes": [
            "supervisor", "macro_analyst", "sentiment_analyst", "risk_manager",
            "technical_analyst", "synthesis",
        ],
        "skip_debate": True,
        "extra_agents": [],
    },
    "trending": {
        "name": "趋势跟踪拓扑",
        "description": "强化技术面和回测，快速响应趋势",
        "nodes": [
            "supervisor", "technical_analyst", "backtest_optimizer",
            "fundamental_analyst", "risk_manager", "synthesis",
        ],
        "skip_debate": False,
        "extra_agents": [],
    },
    "crisis": {
        "name": "危机应对拓扑",
        "description": "全量分析+风险辩论，最大化信息覆盖",
        "nodes": [
            "supervisor", "macro_analyst", "fundamental_analyst",
            "technical_analyst", "sentiment_analyst",
            "bull", "bear", "risk_manager", "synthesis",
        ],
        "skip_debate": False,
        "extra_agents": ["credit_risk_analyst"],
    },
    "low_volatility": {
        "name": "低波动轻量拓扑",
        "description": "精简流程，快速出结论",
        "nodes": [
            "supervisor", "technical_analyst", "fundamental_analyst", "synthesis",
        ],
        "skip_debate": True,
        "extra_agents": [],
    },
}


class TopologyGenerator:
    """Generate and compose agent topologies dynamically (Swarm Morphing)."""

    def __init__(self) -> None:
        self._custom_templates: dict[str, dict[str, Any]] = {}

    def generate_from_regime(self, regime: str, *, symbol: str = "") -> SwarmTopologyDescriptor:
        preset = _REGIME_TOPOLOGY_PRESETS.get(regime)
        if preset is None:
            return self.generate_default(symbol=symbol)
        return self._build_from_preset(regime, preset, symbol=symbol)

    def generate_default(self, *, symbol: str = "") -> SwarmTopologyDescriptor:
        return self._build_from_preset("default", {
            "name": "标准研究拓扑",
            "description": "全量分析师+辩论流程",
            "nodes": [
                "supervisor", "macro_analyst", "fundamental_analyst",
                "technical_analyst", "sentiment_analyst", "backtest_optimizer",
                "bull", "bear", "risk_manager", "synthesis",
            ],
            "skip_debate": False,
            "extra_agents": [],
        }, symbol=symbol)

    def clone_agent(
        self,
        base_role: str,
        *,
        new_id: str | None = None,
        label: str | None = None,
        config_overrides: dict[str, Any] | None = None,
    ) -> TopologyNode:
        template = _AGENT_TEMPLATES.get(base_role) or self._custom_templates.get(base_role)
        if template is None:
            template = {
                "kind": TopologyNodeKind.AGENT,
                "agent_role": base_role,
                "label": label or base_role,
                "config": {},
            }
        node_id = new_id or f"{base_role}_{uuid.uuid4().hex[:6]}"
        config = dict(template.get("config") or {})
        if config_overrides:
            config.update(config_overrides)
        return TopologyNode(
            id=node_id,
            kind=template.get("kind", TopologyNodeKind.AGENT),
            agent_role=template.get("agent_role", base_role),
            label=label or template.get("label", base_role),
            config=config,
        )

    def compose_topology(
        self,
        *,
        agents: list[str],
        include_debate: bool = True,
        symbol: str = "",
    ) -> SwarmTopologyDescriptor:
        nodes: list[TopologyNode] = [
            TopologyNode(id="supervisor", kind=TopologyNodeKind.SUPERVISOR, agent_role="", label="编排者"),
        ]
        for role in agents:
            template = _AGENT_TEMPLATES.get(role)
            if template is None:
                nodes.append(TopologyNode(id=role, kind=TopologyNodeKind.AGENT, agent_role=role, label=role))
            else:
                nodes.append(TopologyNode(
                    id=role,
                    kind=template["kind"],
                    agent_role=template.get("agent_role", role),
                    label=template.get("label", role),
                    config=dict(template.get("config") or {}),
                ))

        if include_debate and "bull" not in agents and "bear" not in agents:
            nodes.append(self.clone_agent("bull", new_id="bull"))
            nodes.append(self.clone_agent("bear", new_id="bear"))

        nodes.append(TopologyNode(id="risk_manager", kind=TopologyNodeKind.AGENT, agent_role="risk_manager", label="风险管理"))
        nodes.append(TopologyNode(id="synthesis", kind=TopologyNodeKind.SYNTHESIS, agent_role="", label="综合决策"))

        edges: list[TopologyEdge] = []
        for i in range(len(nodes) - 1):
            edges.append(TopologyEdge(from_id=nodes[i].id, to_id=nodes[i + 1].id))

        return SwarmTopologyDescriptor(
            schema_version="v1",
            id=f"composed_{uuid.uuid4().hex[:8]}",
            name=f"组合拓扑 ({symbol or '通用'})",
            description=f"动态组合: {', '.join(agents)}",
            nodes=nodes,
            edges=edges,
            entry_node="supervisor",
            exit_node="synthesis",
        )

    def propose_new_agent(self, event_context: dict[str, Any]) -> dict[str, Any]:
        event_type = event_context.get("event_type", "")
        severity = event_context.get("severity", "normal")

        proposals: list[dict[str, Any]] = []

        if event_type in ("credit_downgrade", "sovereign_risk", "default_warning"):
            proposals.append({
                "role": "credit_risk_analyst",
                "label": "信用风险分析师",
                "kind": TopologyNodeKind.AGENT.value,
                "rationale": f"检测到信用风险事件 ({event_type})，建议新增专业信用风险分析节点",
                "config": {"focus": "credit_risk", "data_sources": ["cds_spreads", "credit_ratings", "bond_yields"]},
                "priority": "high" if severity == "critical" else "medium",
            })

        if event_type in ("black_swan", "market_crash", "flash_crash"):
            proposals.append({
                "role": "tail_risk_analyst",
                "label": "尾部风险分析师",
                "kind": TopologyNodeKind.AGENT.value,
                "rationale": f"极端市场事件 ({event_type})，需要尾部风险专项分析",
                "config": {"focus": "tail_risk", "models": ["cvar", "monte_carlo", "stress_test"]},
                "priority": "critical",
            })

        if event_type in ("policy_change", "regulatory_shift"):
            proposals.append({
                "role": "policy_analyst",
                "label": "政策分析师",
                "kind": TopologyNodeKind.AGENT.value,
                "rationale": f"政策变动事件 ({event_type})，建议增加政策解读能力",
                "config": {"focus": "policy", "data_sources": ["central_bank", "regulatory_filings", "government_reports"]},
                "priority": "high",
            })

        if not proposals:
            proposals.append({
                "role": None,
                "label": None,
                "kind": None,
                "rationale": f"当前事件 ({event_type}) 无需新增 Agent，现有拓扑可覆盖",
                "config": {},
                "priority": "low",
            })

        return {
            "event_type": event_type,
            "severity": severity,
            "proposals": proposals,
            "auto_apply": severity == "critical" and len(proposals) == 1,
        }

    def register_template(self, role: str, template: dict[str, Any]) -> None:
        self._custom_templates[role] = template

    def list_templates(self) -> list[dict[str, Any]]:
        all_templates = {**_AGENT_TEMPLATES, **self._custom_templates}
        return [
            {"role": role, "kind": t.get("kind", "").value if hasattr(t.get("kind", ""), "value") else str(t.get("kind", "")),
             "label": t.get("label", role), "config_keys": list((t.get("config") or {}).keys())}
            for role, t in all_templates.items()
        ]

    def list_regime_presets(self) -> list[dict[str, Any]]:
        return [
            {"regime": regime, "name": p["name"], "description": p["description"],
             "node_count": len(p["nodes"]), "skip_debate": p.get("skip_debate", False)}
            for regime, p in _REGIME_TOPOLOGY_PRESETS.items()
        ]

    def _build_from_preset(
        self,
        regime: str,
        preset: dict[str, Any],
        *,
        symbol: str = "",
    ) -> SwarmTopologyDescriptor:
        nodes: list[TopologyNode] = []
        for role_id in preset["nodes"]:
            if role_id == "supervisor":
                nodes.append(TopologyNode(id="supervisor", kind=TopologyNodeKind.SUPERVISOR, agent_role="", label="编排者"))
            elif role_id == "synthesis":
                nodes.append(TopologyNode(id="synthesis", kind=TopologyNodeKind.SYNTHESIS, agent_role="", label="综合决策"))
            else:
                template = _AGENT_TEMPLATES.get(role_id)
                if template:
                    nodes.append(TopologyNode(
                        id=role_id,
                        kind=template["kind"],
                        agent_role=template.get("agent_role", role_id),
                        label=template.get("label", role_id),
                        config=dict(template.get("config") or {}),
                    ))
                else:
                    nodes.append(TopologyNode(id=role_id, kind=TopologyNodeKind.AGENT, agent_role=role_id, label=role_id))

        for extra_role in preset.get("extra_agents") or []:
            nodes.append(self.clone_agent(extra_role, new_id=extra_role))

        edges: list[TopologyEdge] = []
        for i in range(len(nodes) - 1):
            edges.append(TopologyEdge(from_id=nodes[i].id, to_id=nodes[i + 1].id))

        return SwarmTopologyDescriptor(
            schema_version="v1",
            id=f"regime_{regime}_{uuid.uuid4().hex[:6]}",
            name=preset["name"] + (f" ({symbol})" if symbol else ""),
            description=preset["description"],
            nodes=nodes,
            edges=edges,
            entry_node="supervisor",
            exit_node="synthesis",
        )


__all__ = ["TopologyGenerator"]
