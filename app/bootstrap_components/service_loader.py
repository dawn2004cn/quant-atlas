"""Service module preloader 鈥?populates ``@register_service`` registry before ``wire_to``."""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

# Modules that declare @register_service (import side-effect registers them).
_SERVICE_MODULES: tuple[str, ...] = (
    "app.modules.ai_agent.services.ai_committee_selection_service",
    "app.modules.ai_agent.services.investment_committee_service",
    "app.modules.data.services.data_infrastructure_service",
    "app.modules.data.services.gpcw_service",
    "app.modules.data.services.tdx_base_read_service",
    "app.modules.data.services.factor_orthogonalization_service",
    "app.modules.market_data.services.industry_chain_map_service",
    "app.modules.data.services.rdagent_run_service",
    "app.modules.system.services.system.memory_optimization_service",
    "app.modules.system.services.system.task_pipeline_service",
    "app.modules.system.services.ui.evidence_graph_service",
    "app.modules.system.services.ui.user_decision_context_service",
    "app.modules.user.services.user.user_access_policy_service",
)


def preload_service_modules() -> int:
    """Import service modules so ``@register_service`` decorators run.

    Returns the number of modules successfully imported.
    """
    loaded = 0
    for module_name in _SERVICE_MODULES:
        try:
            importlib.import_module(module_name)
            loaded += 1
        except Exception as exc:
            logger.warning("Service preload skipped %s: %s", module_name, exc)
    if loaded:
        logger.debug("Preloaded %d service modules", loaded)
    return loaded


__all__ = ["preload_service_modules"]
