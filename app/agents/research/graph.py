"""Compile the custom trading research graph.

Supervisor → 6 Analysts → Bull/Bear debate → Risk debate → Risk Manager.

Enhanced with EvidenceBlackboard, EvidenceRouter, TieredLLM.

This file is now a thin orchestrator — all node logic lives in
``app.agents.research.nodes`` and conditional routers in ``routing``.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ...core.logger import get_logger
from .catalog import strategy_catalog_text
from .fingpt_forecaster import run_fingpt_forecast_step
from .nodes import (
    backtest_optimizer_node,
    bear_node,
    bull_node,
    chart_vision_node,
    decision_dashboard_node,
    fundamental_analyst_node,
    macro_analyst_node,
    risky_analyst_node,
    risk_manager_node,
    safe_analyst_node,
    sentiment_analyst_node,
    supervisor_node,
    technical_analyst_node,
    write_macro_evidence,
    write_fundamental_evidence,
)
from .routing import ROUTERS
from .state import ResearchState
from .topology_loader import TopologyLoader

logger = get_logger(__name__)


def build_custom_trading_graph(
    llm: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    fingpt_application_service: Any | None = None,
):
    """Build the compiled LangGraph for multi-analyst research.

    :param llm: Chat model for all analyst nodes.
    :param checkpointer: Checkpoint saver (default ``MemorySaver()``).
    :param fingpt_application_service: Optional; write sentiment to MySQL.
    """
    ckpt = checkpointer or MemorySaver()

    # Lazy imports for evidence infrastructure
    from ...agents.evidence_blackboard import get_evidence_blackboard
    from ...agents.evidence_router import create_default_router as get_evidence_router
    from ...agents.tiered_llm import create_orchestrator as get_tiered_llm_orchestrator
    from ...agents.global_tool_wrapper import get_global_tool_wrapper as get_evidence_aware_wrapper

    get_evidence_blackboard()
    get_evidence_router()
    get_tiered_llm_orchestrator()
    get_evidence_aware_wrapper()

    # Catalog (used by backtest node)
    strategy_catalog_text()

    # Node implementations — map node_id → callable
    node_impls: dict[str, Any] = {
        "supervisor": lambda s: supervisor_node(s, llm),
        "macro_analyst": lambda s: macro_analyst_node(s, llm),
        "fundamental_analyst": lambda s: fundamental_analyst_node(s, llm),
        "technical_analyst": lambda s: technical_analyst_node(s, llm),
        "chart_vision": chart_vision_node,
        "sentiment_analyst": lambda s: sentiment_analyst_node(s, llm, fingpt_application_service),
        "backtest_optimizer": lambda s: backtest_optimizer_node(s, llm),
        "bull": lambda s: bull_node(s, llm),
        "bear": lambda s: bear_node(s, llm),
        "risky_analyst": lambda s: risky_analyst_node(s, llm),
        "safe_analyst": lambda s: safe_analyst_node(s, llm),
        "risk_manager": lambda s: risk_manager_node(s, llm),
        "fingpt_forecaster": lambda s: run_fingpt_forecast_step(llm, s, fingpt_application_service),
        "decision_dashboard": lambda s: decision_dashboard_node(s, llm),
        "write_macro_evidence": write_macro_evidence,
        "write_fundamental_evidence": write_fundamental_evidence,
    }

    topology = TopologyLoader.load_default()
    drift = topology.validate_registry(set(node_impls.keys()))
    if drift:
        logger.warning("research topology registry drift: %s", drift)

    g: StateGraph[ResearchState] = StateGraph(ResearchState)
    for node_id, impl in node_impls.items():
        g.add_node(node_id, impl)

    entry = topology.entry_node or "supervisor"
    exit_node = topology.exit_node or "decision_dashboard"
    g.add_edge(START, entry)
    for edge in topology.static_edges():
        g.add_edge(edge.from_id, edge.to_id)
    g.add_edge(exit_node, END)
    for cond in topology.conditional_routers():
        router_fn = ROUTERS.get(cond.router)
        if router_fn is None:
            raise ValueError(f"unknown conditional router: {cond.router}")
        g.add_conditional_edges(cond.from_id, router_fn, cond.mapping)

    return g.compile(checkpointer=ckpt)
