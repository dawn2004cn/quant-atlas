from __future__ import annotations

"""Shared infrastructure helper bindings for Flask bootstrap and Celery workers."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_bound = False


def _register_port_adapters() -> None:
    """Register high-priority domain port adapters with PortRegistry.

    These adapters already exist in infrastructure/ and inherit from domain
    port interfaces, but were never registered with the central registry.
    """
    from app.domain.ports.port_registry import PortRegistry

    # --- Agent swarm & skills ---
    try:
        from app.infrastructure.agent.swarm_orchestrator_adapter import SwarmOrchestratorAdapter
        PortRegistry.register("swarm_orchestrator", SwarmOrchestratorAdapter)
    except ImportError:
        logger.debug("swarm_orchestrator port not available")

    try:
        from app.infrastructure.agent.expert_skill_adapter import ExpertSkillAdapter
        PortRegistry.register("expert_skill", ExpertSkillAdapter)
    except ImportError:
        logger.debug("expert_skill port not available")

    # --- Risk ---
    try:
        from app.infrastructure.risk.risk_gateway import DefaultRiskPreFlight
        PortRegistry.register("risk_preflight", DefaultRiskPreFlight)
    except ImportError:
        logger.debug("risk_preflight port not available")

    try:
        from app.infrastructure.risk.risk_gateway import DefaultPositionSizing
        PortRegistry.register("position_sizing", DefaultPositionSizing)
    except ImportError:
        logger.debug("position_sizing port not available")

    # --- Execution ---
    try:
        from app.infrastructure.execution.qmt_executor import QMTExecutor
        PortRegistry.register("trade_executor", QMTExecutor)
    except ImportError:
        logger.debug("trade_executor port not available")

    # --- Qlib data ---
    try:
        from app.infrastructure.qlib.data_adapter import QlibDataAdapter
        PortRegistry.register("qlib_data_provider", QlibDataAdapter)
    except ImportError:
        logger.debug("qlib_data_provider port not available")

    # --- Tool facade ---
    try:
        from app.infrastructure.agent.tool_facade_adapter import ToolFacadeAdapter
        PortRegistry.register("tool_facade", ToolFacadeAdapter)
    except ImportError:
        logger.debug("tool_facade port not available")


def bind_application_infrastructure(settings: Any = None, *, force: bool = False) -> None:
    """Bind application-layer access helpers (idempotent)."""
    global _bound
    if _bound and not force:
        return

    # Register domain port adapters (idempotent via registry)
    _register_port_adapters()

    from app.bootstrap_components.providers import (
        bind_async_market_helpers_impl,
        create_ai_analysis_adapter,
        create_backtest_engine,
        create_black_litterman_optimizer,
        create_cn_fundamentals_port,
        create_cn_sector_board_port,
        create_config_loader_port,
        create_data_infrastructure_quality_monitor,
        create_data_lineage_tracker_port,
        create_data_quality_port,
        create_default_attribution_analysis,
        create_default_backtest_provider,
        create_default_experiment_repository_impl,
        create_default_position_sizing_impl,
        create_default_risk_preflight_impl,
        create_default_strategy_provider,
        create_default_swarm_runtime_impl,
        create_default_walk_forward_optimizer,
        create_event_store_impl,
        create_expert_skill_port,
        create_in_memory_task_pipeline,
        create_integration_events_impl,
        create_longhu_ingestor,
        create_longhu_mapping_port,
        create_market_data_provider,
        create_markowitz_optimizer,
        create_news_provider,
        create_pre_trade_validation_port,
        create_pytdx_market_port,
        create_qlib_bin_dumper_port,
        create_qlib_data_adapter,
        create_qlib_task_service_impl,
        create_quote_cache_port,
        create_rdagent_artifact_registry_port,
        create_rdagent_job_store_port,
        create_rdagent_validation_port,
        create_shared_memory_manager,
        create_swarm_orchestrator_port,
        create_task_message_store_impl,
        create_task_observer_adapter,
        create_tdx_finance_port,
        create_tdx_local_file_port,
        create_trading_agents_research_port,
    )
    from app.config import get_settings
    from app.infrastructure.di.container import resolve_optional_service as _resolve_optional_service
    from app.infrastructure.repositories.deps import (
        create_integration_probe_repository,
        create_mysql_connection_port,
        create_stock_cache,
        create_stock_metadata_repository,
        create_tdx_base_data_repository,
        create_tdx_block_repository,
        create_tdx_dayk_repository,
        create_tdx_gpcw_repository,
        create_timescale_bar_repository,
    )
    from app.infrastructure.tracing import create_span as _create_span
    from app.modules.data.services.gpcw_service import bind_tdx_gpcw_repository
    from app.modules.data.services.mysql_access import bind_mysql_connection_port
    from app.modules.system.services.helpers import stock_metadata
    from app.modules.system.services.helpers.agent_access import bind_agent_infrastructure
    from app.modules.system.services.helpers.ai_adapter_access import bind_ai_analysis_infrastructure
    from app.modules.system.services.helpers.async_market_access import bind_async_market_helpers
    from app.modules.system.services.helpers.backtest_engine_access import bind_backtest_engine_factory
    from app.modules.system.services.helpers.cn_fundamentals_access import bind_cn_fundamentals_port
    from app.modules.system.services.helpers.cn_sector_board_access import bind_cn_sector_board_port
    from app.modules.system.services.helpers.config_loader_access import bind_config_loader_port
    from app.modules.system.services.helpers.data_infrastructure_access import bind_data_infrastructure
    from app.modules.system.services.helpers.data_quality_access import bind_data_quality_port
    from app.modules.system.services.helpers.events_access import bind_event_infrastructure
    from app.modules.system.services.helpers.integration_probe_access import bind_integration_probe_port
    from app.modules.system.services.helpers.longhu_mapping_access import bind_longhu_mapping_port
    from app.modules.system.services.helpers.market_data_ingestor_access import bind_longhu_ingestor_factory
    from app.modules.system.services.helpers.market_data_provider import bind_market_data_provider
    from app.modules.system.services.helpers.memory_access import bind_memory_infrastructure
    from app.modules.system.services.helpers.metrics_access import bind_metrics_infrastructure
    from app.modules.system.services.helpers.monitoring_access import bind_monitoring_infrastructure
    from app.modules.system.services.helpers.news_provider_access import bind_news_provider
    from app.modules.system.services.helpers.portfolio_access import bind_portfolio_infrastructure
    from app.modules.system.services.helpers.pytdx_access import bind_pytdx_market_port
    from app.modules.system.services.helpers.qlib_access import bind_qlib_infrastructure
    from app.modules.system.services.helpers.quote_cache_access import bind_quote_cache_port
    from app.modules.system.services.helpers.rdagent_access import bind_rdagent_infrastructure
    from app.modules.system.services.helpers.research_access import bind_research_infrastructure
    from app.modules.system.services.helpers.service_resolver_access import bind_service_resolver
    from app.modules.system.services.helpers.strategy_access import bind_strategy_infrastructure
    from app.modules.system.services.helpers.strategy_providers_access import bind_strategy_provider_factories
    from app.modules.system.services.helpers.task_message_access import bind_task_message_store
    from app.modules.system.services.helpers.task_ops_access import bind_task_ops_infrastructure
    from app.modules.system.services.helpers.task_pipeline_access import bind_task_pipeline_infrastructure
    from app.modules.system.services.helpers.tdx_block_repository_access import bind_tdx_block_read_port
    from app.modules.system.services.helpers.tdx_data_repository_access import (
        bind_tdx_base_data_write_port,
        bind_tdx_dayk_write_port,
    )
    from app.modules.system.services.helpers.tdx_finance_access import bind_tdx_finance_port
    from app.modules.system.services.helpers.tdx_local_access import bind_tdx_local_file_port
    from app.modules.system.services.helpers.timescale_bar_access import bind_timescale_bar_port
    from app.modules.system.services.helpers.tracing_access import bind_tracing
    from app.modules.system.services.helpers.trading_risk_access import bind_trading_risk_defaults

    s = settings or get_settings()
    stock_metadata.bind_stock_metadata_repository(create_stock_metadata_repository(s))
    bind_mysql_connection_port(create_mysql_connection_port(s))
    bind_tdx_gpcw_repository(create_tdx_gpcw_repository(s))
    bind_tdx_block_read_port(create_tdx_block_repository(s))
    bind_tdx_dayk_write_port(create_tdx_dayk_repository(s))
    bind_tdx_base_data_write_port(create_tdx_base_data_repository(s))
    bind_timescale_bar_port(create_timescale_bar_repository(s))
    bind_integration_probe_port(create_integration_probe_repository(s))
    bind_market_data_provider(create_market_data_provider())
    bind_tdx_local_file_port(create_tdx_local_file_port())
    bind_pytdx_market_port(create_pytdx_market_port())
    bind_cn_fundamentals_port(create_cn_fundamentals_port())
    bind_cn_sector_board_port(create_cn_sector_board_port())
    bind_news_provider(create_news_provider())
    wrap_async, standalone_async = bind_async_market_helpers_impl()
    bind_async_market_helpers(
        wrap_sync_provider=wrap_async,
        standalone_factory=standalone_async,
    )
    bind_strategy_provider_factories(
        strategy_factory=create_default_strategy_provider,
        backtest_factory=create_default_backtest_provider,
    )
    bind_backtest_engine_factory(create_backtest_engine)
    bind_quote_cache_port(create_quote_cache_port())
    bind_longhu_mapping_port(create_longhu_mapping_port())
    bind_data_quality_port(create_data_quality_port())
    bind_config_loader_port(create_config_loader_port())
    bind_longhu_ingestor_factory(create_longhu_ingestor)
    bind_qlib_infrastructure(
        create_data_adapter=create_qlib_data_adapter,
        bin_dumper=create_qlib_bin_dumper_port(),
        task_service_factory=create_qlib_task_service_impl,
    )
    bind_rdagent_infrastructure(
        job_store_factory=create_rdagent_job_store_port,
        artifact_registry_factory=create_rdagent_artifact_registry_port,
        validation=create_rdagent_validation_port(),
    )
    bind_trading_risk_defaults(
        pre_trade_validator_factory=create_pre_trade_validation_port,
        risk_preflight_factory=create_default_risk_preflight_impl,
        position_sizing_factory=create_default_position_sizing_impl,
    )
    bind_service_resolver(_resolve_optional_service)
    bind_tdx_finance_port(create_tdx_finance_port())
    bind_tracing(create_span=_create_span)
    bind_event_infrastructure(
        event_store_factory=create_event_store_impl,
        integration_events_factory=create_integration_events_impl,
    )
    bind_task_message_store(create_task_message_store_impl)
    from app.infrastructure.adapters.celery_task_admin import (
        inspect_snapshot,
        revoke_task,
        task_status,
    )

    bind_task_ops_infrastructure(
        inspect_snapshot=inspect_snapshot,
        task_status=task_status,
        revoke_task=revoke_task,
    )
    bind_agent_infrastructure(
        swarm_orchestrator_factory=create_swarm_orchestrator_port,
        expert_skill_factory=create_expert_skill_port,
        experiment_repository_factory=create_default_experiment_repository_impl,
        swarm_runtime_factory=create_default_swarm_runtime_impl,
    )
    bind_task_pipeline_infrastructure(
        pipeline_factory=create_in_memory_task_pipeline,
        observer_factory=create_task_observer_adapter,
    )
    bind_memory_infrastructure(manager_factory=create_shared_memory_manager)

    def _check_table_freshness(table: str, max_delay_minutes: int) -> bool:
        from app.config import get_settings
        from app.infrastructure.monitoring.sentinel import DataFreshnessSentinel

        return DataFreshnessSentinel(get_settings()).check_freshness(
            table,
            max_delay_minutes=max_delay_minutes,
        )

    def _metrics_summary() -> dict[str, object]:
        from app.infrastructure.metrics import active_users, swarm_tasks_running

        return {
            "running_tasks": swarm_tasks_running._value.get(),
            "active_users": active_users._value.get(),
        }

    from app.infrastructure.metrics import get_metrics, get_metrics_content_type

    bind_monitoring_infrastructure(check_table_freshness=_check_table_freshness)
    bind_metrics_infrastructure(
        get_metrics=get_metrics,
        get_metrics_content_type=get_metrics_content_type,
        get_metrics_summary=_metrics_summary,
    )
    bind_strategy_infrastructure(walk_forward_factory=create_default_walk_forward_optimizer)
    bind_portfolio_infrastructure(
        markowitz_factory=create_markowitz_optimizer,
        black_litterman_factory=create_black_litterman_optimizer,
        attribution_factory=create_default_attribution_analysis,
    )
    bind_data_infrastructure(
        quality_monitor_factory=create_data_infrastructure_quality_monitor,
        lineage_tracker_factory=create_data_lineage_tracker_port,
    )
    bind_ai_analysis_infrastructure(adapter_factory=create_ai_analysis_adapter)
    bind_research_infrastructure(research_port_factory=create_trading_agents_research_port)

    _ = create_stock_cache  # ensure cache module loads with bindings
    _bound = True
    logger.debug("application infrastructure helpers bound")
