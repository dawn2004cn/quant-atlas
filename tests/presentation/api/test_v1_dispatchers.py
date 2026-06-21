"""Consolidated dispatcher smoke tests for v1 giant-route splits (phases 8–17)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.presentation.api.route_deps import TdxBaseRouteDeps
from app.presentation.api.v1.data_optimizer._helpers import parse_symbols_param
from app.presentation.api.v1.market_aux.runtime import MarketAuxRuntime
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1.signal_flag._helpers import parse_signal_flag_max_stocks
from app.presentation.api.v1.signal_flag.runtime import SignalFlagRuntime
from app.presentation.api.v1.tdx_base.runtime import TdxBaseRuntime
from app.presentation.api.v1_context import ApiV1Context


def _assert_callable(*fns: object) -> None:
    for fn in fns:
        assert callable(fn)


# --- Phase 8: hot_sectors, task_ops ---


def test_hot_sectors_dispatcher():
    from app.presentation.api.routes_v1_hot_sectors import register_hot_sector_routes

    assert callable(register_hot_sector_routes)


def test_hot_sectors_submodules():
    from app.presentation.api.v1.hot_sectors import (
        register_hot_sector_ingest_routes,
        register_hot_sector_list_routes,
        register_hot_sector_member_routes,
    )

    _assert_callable(
        register_hot_sector_list_routes,
        register_hot_sector_ingest_routes,
        register_hot_sector_member_routes,
    )


def test_task_ops_dispatcher():
    from app.presentation.api.routes_v1_task_ops import register_task_ops_routes

    assert callable(register_task_ops_routes)


def test_task_ops_submodules():
    from app.presentation.api.v1.task_ops import (
        register_task_ops_batch_routes,
        register_task_ops_celery_routes,
        register_task_ops_sync_routes,
    )

    _assert_callable(
        register_task_ops_celery_routes,
        register_task_ops_sync_routes,
        register_task_ops_batch_routes,
    )


# --- Phase 9: lifecycle ---


def test_lifecycle_dispatcher():
    from app.presentation.api.routes_v1_lifecycle import register_lifecycle_routes

    assert callable(register_lifecycle_routes)


def test_lifecycle_submodules():
    from app.presentation.api.v1.lifecycle import (
        register_lifecycle_data_routes,
        register_lifecycle_execution_routes,
        register_lifecycle_monitoring_routes,
        register_lifecycle_research_routes,
        register_lifecycle_simulation_routes,
    )

    _assert_callable(
        register_lifecycle_data_routes,
        register_lifecycle_research_routes,
        register_lifecycle_simulation_routes,
        register_lifecycle_execution_routes,
        register_lifecycle_monitoring_routes,
    )


def test_lifecycle_runtime_factories():
    from app.presentation.api.v1.lifecycle.runtime import (
        get_alpha_mining_services,
        get_execution_services,
        get_monitoring_services,
        get_simulation_services,
        get_tick_services,
    )

    assert len(get_tick_services()) == 3
    assert len(get_alpha_mining_services()) == 3
    assert len(get_simulation_services()) == 3
    assert len(get_execution_services()) == 3
    assert len(get_monitoring_services()) == 4


# --- Phase 10: tdx_base ---


def test_tdx_base_dispatcher():
    from app.presentation.api.routes_v1_tdx_base import register_tdx_base_routes

    assert callable(register_tdx_base_routes)


def test_tdx_base_submodules():
    from app.presentation.api.v1.tdx_base import (
        register_tdx_base_block_routes,
        register_tdx_base_finance_routes,
        register_tdx_base_ingest_routes,
        register_tdx_base_watchlist_routes,
    )

    _assert_callable(
        register_tdx_base_ingest_routes,
        register_tdx_base_block_routes,
        register_tdx_base_watchlist_routes,
        register_tdx_base_finance_routes,
    )


def test_tdx_base_runtime_from_deps():
    svc = MagicMock()
    runtime = TdxBaseRuntime.from_deps(
        TdxBaseRouteDeps(tdx_base_read_service=svc, enable_legacy_response_fields=True)
    )
    assert runtime.legacy is True
    assert runtime.tdx_read is svc


# --- Phase 11: optimization ---


def test_optimization_dispatcher():
    from app.presentation.api.routes_v1_optimization import register_optimization_routes

    assert callable(register_optimization_routes)


def test_optimization_submodules():
    from app.presentation.api.v1.optimization import (
        register_optimization_budget_routes,
        register_optimization_compliance_routes,
        register_optimization_dual_path_routes,
        register_optimization_evolution_routes,
    )

    _assert_callable(
        register_optimization_dual_path_routes,
        register_optimization_compliance_routes,
        register_optimization_budget_routes,
        register_optimization_evolution_routes,
    )


def test_optimization_runtime_factories():
    from app.presentation.api.v1.optimization.runtime import (
        get_anti_decay_evolution_service,
        get_complexity_budget_service,
        get_compliance_service,
        get_dual_path_router,
    )

    assert get_dual_path_router() is not None
    assert get_compliance_service() is not None
    assert get_complexity_budget_service() is not None
    assert get_anti_decay_evolution_service() is not None


# --- Phase 12: signal_flag, market_aux ---


def test_signal_flag_dispatcher():
    from app.presentation.api.routes_v1_signal_flag import register_signal_flag_routes

    assert callable(register_signal_flag_routes)


def test_signal_flag_submodules():
    from app.presentation.api.v1.signal_flag import (
        register_signal_flag_backfill_routes,
        register_signal_flag_query_routes,
        register_signal_flag_scan_routes,
    )

    _assert_callable(
        register_signal_flag_query_routes,
        register_signal_flag_scan_routes,
        register_signal_flag_backfill_routes,
    )


def test_market_aux_dispatcher():
    from app.presentation.api.routes_v1_market_aux import register_market_aux_routes

    assert callable(register_market_aux_routes)


def test_market_aux_submodules():
    from app.presentation.api.v1.market_aux import (
        register_market_aux_feed_routes,
        register_market_aux_pulse_routes,
        register_market_aux_refresh_routes,
    )

    _assert_callable(
        register_market_aux_feed_routes,
        register_market_aux_pulse_routes,
        register_market_aux_refresh_routes,
    )


def test_parse_signal_flag_max_stocks_defaults():
    assert parse_signal_flag_max_stocks({}) == 800
    assert parse_signal_flag_max_stocks({"max_stocks": 0}) == 0
    assert parse_signal_flag_max_stocks({"max_stocks": 100}) == 100


def test_signal_flag_runtime_require_service():
    ctx = ApiV1Context(signal_flag_service=MagicMock())
    runtime = SignalFlagRuntime(ctx=ctx)
    assert runtime.require_service() is ctx.signal_flag_service


def test_market_aux_runtime_properties():
    ctx = ApiV1Context(
        basic_market_data_service=MagicMock(),
        market_narrative_service=MagicMock(),
        enable_legacy_response_fields=True,
    )
    runtime = MarketAuxRuntime(ctx=ctx)
    assert runtime.legacy is True
    assert runtime.basic_market_data_service is ctx.basic_market_data_service


# --- Phase 13: retail_assistant, data_optimizer ---


def test_retail_assistant_dispatcher():
    from app.presentation.api.routes_v1_retail_assistant import register_retail_assistant_routes

    assert callable(register_retail_assistant_routes)


def test_retail_assistant_submodules():
    from app.presentation.api.v1.retail_assistant import (
        register_retail_assistant_hub_routes,
        register_retail_assistant_insight_routes,
        register_retail_assistant_psychology_routes,
        register_retail_assistant_shadow_routes,
    )

    _assert_callable(
        register_retail_assistant_hub_routes,
        register_retail_assistant_insight_routes,
        register_retail_assistant_psychology_routes,
        register_retail_assistant_shadow_routes,
    )


def test_data_optimizer_dispatcher():
    from app.presentation.api.routes_v1_data_optimizer import register_data_optimizer_routes

    assert callable(register_data_optimizer_routes)


def test_data_optimizer_submodules():
    from app.presentation.api.v1.data_optimizer import (
        register_data_optimizer_scenario_routes,
        register_data_optimizer_tdx_routes,
        register_data_optimizer_write_routes,
    )

    _assert_callable(
        register_data_optimizer_scenario_routes,
        register_data_optimizer_tdx_routes,
        register_data_optimizer_write_routes,
    )


def test_data_optimizer_parse_symbols():
    assert parse_symbols_param("600519, 000001") == ["600519", "000001"]


def test_retail_assistant_runtime_legacy_default():
    runtime = RetailAssistantRuntime(ctx=ApiV1Context())
    assert runtime.legacy is True
    assert runtime.hub_service is None


# --- Phase 14: provenance, wisdom_mesh ---


def test_provenance_dispatcher_and_blueprint_alias():
    from app.presentation.api.routes_v1_provenance import blueprint, register_provenance_routes

    assert callable(register_provenance_routes)
    assert blueprint.url_prefix == "/provenance"


def test_provenance_submodules():
    from app.presentation.api.v1.provenance import (
        register_provenance_dashboard_routes,
        register_provenance_fingerprint_routes,
    )

    _assert_callable(
        register_provenance_fingerprint_routes,
        register_provenance_dashboard_routes,
    )


def test_wisdom_mesh_dispatcher():
    from app.presentation.api.routes_v1_wisdom_mesh import register_wisdom_mesh_routes

    assert callable(register_wisdom_mesh_routes)


def test_wisdom_mesh_submodules():
    from app.presentation.api.v1.wisdom_mesh import (
        register_wisdom_mesh_leaderboard_routes,
        register_wisdom_mesh_strategy_routes,
    )

    _assert_callable(
        register_wisdom_mesh_strategy_routes,
        register_wisdom_mesh_leaderboard_routes,
    )


def test_wisdom_mesh_blueprint_prefix():
    from app.presentation.api.v1.wisdom_mesh import wisdom_mesh_blueprint

    assert wisdom_mesh_blueprint.url_prefix == "/wisdom-mesh"


# --- Phase 15: strategy_synthesis, one_click, risk_companion ---


def test_strategy_synthesis_dispatcher():
    from app.presentation.api.routes_v1_strategy_synthesis import register_strategy_synthesis_routes

    assert callable(register_strategy_synthesis_routes)


def test_strategy_synthesis_submodules():
    from app.presentation.api.v1.strategy_synthesis import (
        register_strategy_synthesis_evidence_routes,
        register_strategy_synthesis_pipeline_routes,
    )

    _assert_callable(
        register_strategy_synthesis_pipeline_routes,
        register_strategy_synthesis_evidence_routes,
    )


def test_one_click_dispatcher():
    from app.presentation.api.routes_v1_one_click import register_one_click_routes

    assert callable(register_one_click_routes)


def test_one_click_submodules():
    from app.presentation.api.v1.one_click import (
        register_one_click_action_routes,
        register_one_click_evidence_routes,
    )

    _assert_callable(
        register_one_click_action_routes,
        register_one_click_evidence_routes,
    )


def test_risk_companion_dispatcher():
    from app.presentation.api.routes_v1_risk_companion import register_risk_companion_routes

    assert callable(register_risk_companion_routes)


def test_risk_companion_submodules():
    from app.presentation.api.v1.risk_companion import (
        register_risk_companion_detect_routes,
        register_risk_companion_profile_routes,
    )

    _assert_callable(
        register_risk_companion_detect_routes,
        register_risk_companion_profile_routes,
    )


def test_phase15_nested_blueprint_prefixes():
    from app.presentation.api.v1.one_click import one_click_blueprint
    from app.presentation.api.v1.risk_companion import risk_companion_blueprint
    from app.presentation.api.v1.strategy_synthesis import strategy_synthesis_blueprint

    assert strategy_synthesis_blueprint.url_prefix == "/strategy-synthesis"
    assert one_click_blueprint.url_prefix == "/one-click"
    assert risk_companion_blueprint.url_prefix == "/risk/companion"


# --- Phase 16: ai_hedge_fund, attribution, decision_provenance ---


def test_ai_hedge_fund_dispatcher():
    from app.presentation.api.routes_v1_ai_hedge_fund import register_ai_hedge_fund_routes

    assert callable(register_ai_hedge_fund_routes)


def test_ai_hedge_fund_submodules():
    from app.presentation.api.v1.ai_hedge_fund import (
        AiHedgeFundRuntime,
        register_ai_hedge_fund_analyze_routes,
        register_ai_hedge_fund_query_routes,
    )

    _assert_callable(register_ai_hedge_fund_analyze_routes, register_ai_hedge_fund_query_routes)
    assert AiHedgeFundRuntime(ctx=MagicMock(spec=ApiV1Context)).ctx is not None


def test_attribution_dispatcher():
    from app.presentation.api.routes_v1_attribution import (
        attribution_bp,
        register_attribution_routes,
    )

    assert callable(register_attribution_routes)
    assert attribution_bp.url_prefix == "/attribution"


def test_attribution_submodules():
    from app.presentation.api.v1.attribution import (
        AttributionRuntime,
        register_attribution_analyze_routes,
        register_attribution_whatif_routes,
    )
    from app.presentation.api.v1.attribution._helpers import DEFAULT_POSITIONS

    _assert_callable(register_attribution_analyze_routes, register_attribution_whatif_routes)
    assert len(DEFAULT_POSITIONS) == 3
    assert AttributionRuntime(ctx=None).market_service is None


def test_decision_provenance_dispatcher():
    from app.presentation.api.routes_v1_decision_provenance import register_decision_provenance_routes

    assert callable(register_decision_provenance_routes)


def test_decision_provenance_submodules():
    from app.presentation.api.v1.decision_provenance import (
        DecisionProvenanceRuntime,
        register_decision_lifecycle_routes,
        register_evidence_graph_routes,
        register_sequence_chain_routes,
    )

    _assert_callable(
        register_sequence_chain_routes,
        register_evidence_graph_routes,
        register_decision_lifecycle_routes,
    )
    trace_id = DecisionProvenanceRuntime(ctx=MagicMock(spec=ApiV1Context)).new_trace_id()
    assert trace_id.startswith("trace-")


# --- Phase 17: swarm_topology, alpha_marketplace, mesh ---


def test_swarm_topology_dispatcher():
    from app.presentation.api.routes_v1_swarm_topology import register_swarm_topology_routes

    assert callable(register_swarm_topology_routes)


def test_swarm_topology_submodules():
    from app.presentation.api.v1.swarm_topology import (
        SwarmTopologyRuntime,
        register_swarm_topology_adaptive_routes,
        register_swarm_topology_core_routes,
    )

    _assert_callable(register_swarm_topology_core_routes, register_swarm_topology_adaptive_routes)
    assert SwarmTopologyRuntime(ctx=MagicMock(spec=ApiV1Context)).legacy is not None


def test_alpha_marketplace_dispatcher():
    from app.presentation.api.routes_v1_alpha_marketplace import register_alpha_marketplace_routes

    assert callable(register_alpha_marketplace_routes)


def test_alpha_marketplace_submodules():
    from app.presentation.api.v1.alpha_marketplace import (
        register_alpha_marketplace_reputation_routes,
        register_alpha_marketplace_trade_routes,
    )
    from app.presentation.api.v1.alpha_marketplace._helpers import get_compliance_service, get_marketplace_service

    _assert_callable(register_alpha_marketplace_trade_routes, register_alpha_marketplace_reputation_routes)
    assert callable(get_marketplace_service)
    assert callable(get_compliance_service)


def test_mesh_dispatcher():
    from app.presentation.api.routes_v1_mesh import register_mesh_routes

    assert callable(register_mesh_routes)


def test_mesh_submodules():
    from app.presentation.api.v1.mesh import (
        MeshRuntime,
        register_mesh_gateway_routes,
        register_mesh_perception_routes,
    )

    _assert_callable(register_mesh_gateway_routes, register_mesh_perception_routes)
    assert MeshRuntime(ctx=MagicMock(spec=ApiV1Context)).gateway_service is None
