"""Batch fix all stale application.services imports in route files."""

import glob
import os

os.chdir(r"E:\project\workspace\myrepo\quant-atlas")

# Mapping: old import line -> new import line
replacements = [
    # factor/alpha_factory_orchestrator
    ("from ...application.services.factor.alpha_factory_orchestrator import get_orchestrator",
     "from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator"),

    # research pipeline
    ("from ...application.services.research.research_pipeline_snapshot import build_research_pipeline_snapshot",
     "from app.modules.data.services.research_pipeline_snapshot import build_research_pipeline_snapshot"),

    # data services
    ("from ...application.services.data.data_router_service import MarketDataService",
     "from app.modules.data.services.data_router_service import MarketDataService"),
    ("from ...application.services.data.history_row_validator import validate_ohlcv_history_rows",
     "from app.modules.data.services.history_row_validator import validate_ohlcv_history_rows"),
    ("from ...application.services.data.gpcw_service import get_gpcw_service",
     "from app.modules.data.services.gpcw_service import get_gpcw_service"),
    ("from ...application.services.data.pytdx_api_service import PytdxApiService",
     "from app.modules.data.services.pytdx_api_service import PytdxApiService"),
    ("from ...application.services.data.pytdx_market_data_service import get_pytdx_market_data_service",
     "from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service"),
    ("from ...application.services.data.tdx_base_data_service import TdxBaseDataService",
     "from app.modules.data.services.tdx_base_data_service import TdxBaseDataService"),
    ("from ...application.services.data.tdx_block_stats_service import TdxBlockStatsService",
     "from app.modules.data.services.tdx_block_stats_service import TdxBlockStatsService"),
    ("from ...application.services.data.tdx_block_membership_cache import",
     "from app.modules.data.services.tdx_block_membership_cache import"),

    # ui services
    ("from ...application.services.ui.evidence_graph_service import get_evidence_graph_service",
     "from app.modules.system.services.ui.evidence_graph_service import get_evidence_graph_service"),
    ("from ...application.services.ui.evidence_graph_service import",
     "from app.modules.system.services.ui.evidence_graph_service import"),
    ("from ...application.services.ui.decision_provenance_service import",
     "from app.modules.system.services.ui.decision_provenance_service import"),
    ("from ...application.services.ui.decision_trace_service import",
     "from app.modules.system.services/ui/decision_trace_service import"),
    ("from ...application.services.ui.decision_review_queue import get_review_queue",
     "from app.modules.system.services/ui/decision_review_queue import get_review_queue"),
    ("from ...application.services.ui.decision_review_queue import",
     "from app.modules.system/services/ui/decision_review_queue import"),
    ("from ...application.services.ui.data_freshness_service import enrich_market_payload",
     "from app.modules.system/services/ui/data_freshness_service import enrich_market_payload"),
    ("from ...application.services.ui.attribution_timeline_service import",
     "from app.modules/system/services/ui/attribution_timeline_service import"),

    # ai
    ("from ...application.services.ai.decision_feedback_service import",
     "from app/modules/ai_agent/services/ai/decision_feedback_service import"),

    # system
    ("from ...application.services.system.system_pulse_service import SystemPulseService",
     "from app.modules/system/services/system/system_pulse_service import SystemPulseService"),
    ("from ...application.services.system.realtime_gateway_service import",
     "from app.modules/system/services/system/realtime_gateway_service import"),

    # trading
    ("from ...application.services.trading.trade_plan_adoption_service import TradePlanAdoptionService",
     "from app/modules/execution/services/trade_plan_adoption_service import TradePlanAdoptionService"),
    ("from ...application.services.trading.trade_outcome_review_service import get_trade_review_service",
     "from app/modules/execution/services/trade_outcome_review_service import get_trade_review_service"),

    # monitoring
    ("from ...application.services.monitoring.trace_query_service import TraceQueryService",
     "from app/modules/system/services/monitoring/trace_query_service import TraceQueryService"),

    # ui workflow/focus
    ("from ...application.services.ui.workflow_hub_service import WorkflowHubService",
     "from app/modules/system/services/ui/workflow_hub_service import WorkflowHubService"),
    ("from ...application.services.ui.focus_context_service import FocusContextService",
     "from app/modules/system/services/ui/focus_context_service import FocusContextService"),
    ("from ...application.services.ui.decision_flow_contract_service import",
     "from app/modules/system/services/ui/decision_flow_contract_service import"),

    # orchestration
    ("from app.application.services.orchestration.agent_topology_service import",
     "from app.modules/system/services/orchestration/agent_topology_service import"),

    # strategies
    ("from app.application.services.strategies.strategy_synthesizer_service import",
     "from app.application.services.strategies/strategy_synthesizer_service import"),

    # helpers
    ("from ...application.services.helpers.data_optimizer_access import",
     "from app/modules/system/services/helpers/data_optimizer_access import"),
    ("from ...application.services.scenario_optimizer_service import",
     "from app.modules/strategy/services/strategy/scenario_optimizer_service import"),
    ("from ...application.services.helpers.task_ops_access import",
     "from app/modules/system/services/helpers/task_ops_access import"),
]

# Also fix non-relative imports
replacements.extend([
    ("from ...application.services.quant_agent_service import QuantAgentService",
     "from app.presentation.api.quant_agent_service import QuantAgentService"),
    ("from ...application.services.llm_user_config import",
     "from app.modules/system/services/config/llm_user_config import"),
])

fixed_count = 0
for filepath in glob.glob("app/presentation/api/routes_v1_*.py"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in replacements:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        fixed_count += 1
        print(f"  Fixed: {filepath}")

print(f"\nFixed {fixed_count} files")
