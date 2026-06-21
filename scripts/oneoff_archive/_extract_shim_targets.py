import os, re

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")

shim_map = {
    "app/application/services/alpha/alpha_marketplace_service.py": "app.modules.system.services.alpha.alpha_marketplace_service",
    "app/application/services/alpha/tokenized_alpha_service.py": "app.modules.system.services.alpha.tokenized_alpha_service",
    "app/application/services/alpha/wallet_service.py": "app.modules.system.services.alpha.wallet_service",
    "app/application/services/data/basic_data_scheduler.py": "app.modules.data.services.basic_data_scheduler",
    "app/application/services/data/basic_market_data_service.py": "app.modules.data.services.basic_market_data_service",
    "app/application/services/data/data_router_service.py": "app.modules.data.services.data_router_service",
    "app/application/services/data/gpcw_data_service.py": "app.modules.data.services.gpcw_data_service",
    "app/application/services/data/gpcw_service.py": "app.modules.data.services.gpcw_service",
    "app/application/services/data/pytdx_api_service.py": "app.modules.data.services.pytdx_api_service",
    "app/application/services/data/pytdx_market_data_service.py": "app.modules.data.services.pytdx_market_data_service",
    "app/application/services/data/tdx_base_data_service.py": "app.modules.data.services.tdx_base_data_service",
    "app/application/services/data/tdx_block_stats_service.py": "app.modules.data.services.tdx_block_stats_service",
    "app/application/services/data/tdx_dayk_sync_service.py": "app.modules.data.services.tdx_dayk_sync_service",
    "app/application/services/factor/factor_catalog_service.py": "app.modules.data.services.factor_catalog_service",
    "app/application/services/factor/factor_orthogonalization_service.py": "app.modules.data.services.factor_orthogonalization_service",
    "app/application/services/immune/immune_agent_service.py": "app.modules.system.services.immune_agent_service",
    "app/application/services/immune/immune_orchestrator.py": "app.modules.system.services.immune_orchestrator",
    "app/application/services/immune/immune_service.py": "app.modules.system.services.immune_service",
    "app/application/services/intent_decomposer.py": "app.modules.ai_agent.services.intention.intent_decomposer",
    "app/application/services/orchestration/adaptive_topology_service.py": "app.modules.system.services.adaptive_topology_service",
    "app/application/services/orchestration/agent_topology_service.py": "app.modules.system.services.agent_topology_service",
    "app/application/services/orchestration/arbiter_review_learning_service.py": "app.modules.system.services.arbiter_review_learning_service",
    "app/application/services/orchestration/arbiter_service.py": "app.modules.system.services.arbiter_service",
    "app/application/services/orchestration/canvas_event_bridge.py": "app.modules.system.services.canvas_event_bridge",
    "app/application/services/orchestration/correction_intent_service.py": "app.modules.system.services.correction_intent_service",
    "app/application/services/orchestration/debate_arbiter_service.py": "app.modules.system.services.debate_arbiter_service",
    "app/application/services/orchestration/meta_arbiter_service.py": "app.modules.system.services.meta_arbiter_service",
    "app/application/services/orchestration/sequence_chain_service.py": "app.modules.system.services.sequence_chain_service",
    "app/application/services/orchestration/swarm_topology_service.py": "app.modules.system.services.swarm_topology_service",
    "app/application/services/orchestration/topology_generator.py": "app.modules.system.services.topology_generator",
    "app/application/services/portfolio/investment_manager_service.py": "app.modules.execution.services.investment_manager_service",
    "app/application/services/portfolio/portfolio_local_memory.py": "app.modules.system.services.portfolio_local_memory",
    "app/application/services/prompt_decision_bridge.py": "app.modules.ai_agent.services.prompt_decision_bridge",
    "app/application/services/qlib/qlib_pipeline_service.py": "app.modules.data.services.qlib_pipeline_service",
    "app/application/services/qlib/qlib_service.py": "app.modules.data.services.qlib_service",
    "app/application/services/research/moments_service.py": "app.modules.data.services.moments_service",
    "app/application/services/research/research_pipeline_snapshot.py": "app.modules.data.services.research_pipeline_snapshot",
    "app/application/services/social/moments_service.py": "app.modules.data.services.moments_service",
    "app/application/services/strategy/scanner_service.py": "app.modules.strategy.services.strategy.scanner_service",
    "app/application/services/strategy/signal_flag_service.py": "app.modules.strategy.services.strategy.signal_flag_service",
    "app/application/services/tool_facade_service.py": "app.modules.system.services.tools.tool_facade_service",
    "app/application/services/trading/investment_manager_service.py": "app.modules.execution.services.investment_manager_service",
    "app/application/services/trading/trade_plan_adoption_service.py": "app.modules.execution.services.trade_plan_adoption_service",
    "app/application/services/ui/attribution_timeline_service.py": "app.modules.system.services.ui.attribution_timeline_service",
    "app/application/services/ui/data_freshness_service.py": "app.modules.system.services.ui.data_freshness_service",
    "app/application/services/ui/decision_brief_service.py": "app.modules.system.services.ui.decision_brief_service",
    "app/application/services/ui/decision_event_journal.py": "app.modules.system.services.ui.decision_event_journal",
    "app/application/services/ui/decision_flow_contract_service.py": "app.modules.system.services.ui.decision_flow_contract_service",
    "app/application/services/ui/decision_provenance_service.py": "app.modules.system.services.ui.decision_provenance_service",
    "app/application/services/ui/decision_replay_space_service.py": "app.modules.system.services.ui.decision_replay_space_service",
    "app/application/services/ui/decision_review_queue.py": "app.modules.system.services.ui.decision_review_queue",
    "app/application/services/ui/decision_snapshot_service.py": "app.modules.system.services.ui.decision_snapshot_service",
    "app/application/services/ui/decision_theater_service.py": "app.modules.system.services.ui.decision_theater_service",
    "app/application/services/ui/decision_trace_service.py": "app.modules.system.services.ui.decision_trace_service",
    "app/application/services/ui/evidence_graph_service.py": "app.modules.system.services.ui.evidence_graph_service",
    "app/application/services/ui/evidence_traceability_service.py": "app.modules.system.services.ui.evidence_traceability_service",
    "app/application/services/ui/focus_context_service.py": "app.modules.system.services.ui.focus_context_service",
    "app/application/services/ui/live_research_document_service.py": "app.modules.system.services.ui.live_research_document_service",
    "app/application/services/ui/predictive_preload_service.py": "app.modules.system.services.ui.predictive_preload_service",
    "app/application/services/ui/sector_context_service.py": "app.modules.system.services.ui.sector_context_service",
    "app/application/services/ui/stock_discovery_service.py": "app.modules.system.services.ui.stock_discovery_service",
    "app/application/services/ui/user_decision_context_service.py": "app.modules.system.services.ui.user_decision_context_service",
    "app/application/services/ui/workflow_hub_service.py": "app.modules.system.services.ui.workflow_hub_service",
    "app/application/services/user/user_service.py": "app.modules.user.services.user.user_service",
}

for shim_path in sorted(shim_map.keys()):
    module_path = shim_map[shim_path]
    target_path = "app/" + module_path.replace(".", "/") + ".py"

    if not os.path.exists(target_path):
        print(f"{shim_path}|||{module_path}|||TARGET_NOT_FOUND")
        continue

    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    all_match = re.search(r"^__all__\s*=\s*\[(.*?)\]", content, re.DOTALL | re.MULTILINE)
    if all_match:
        symbols = re.findall(r'["\x27](\w+)["\x27]', all_match.group(1))
    else:
        symbols = []
        for m in re.finditer(r"^(?:class|def)\s+(\w+)", content, re.MULTILINE):
            name = m.group(1)
            if not name.startswith("_"):
                symbols.append(name)

    print(f"{shim_path}|||{module_path}|||{symbols}")
