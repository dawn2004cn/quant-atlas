"""Providers configuration with lazy loading support."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def _lazy_news_provider() -> Any:
    """Lazy load news provider."""
    try:
        from app.infrastructure.providers.news import AkshareNewsProvider
        return AkshareNewsProvider()
    except Exception as exc:
        logger.warning("AkshareNewsProvider unavailable: %s", exc, exc_info=True)
        return None


def _lazy_quote_gateway() -> Any:
    """Lazy load quote gateway."""
    try:
        from app.infrastructure.adapters.tencent_quote_gateway import TencentQuoteGateway
        return TencentQuoteGateway()
    except Exception as exc:
        logger.warning("TencentQuoteGateway unavailable: %s", exc, exc_info=True)
        return None


def _lazy_web_search_provider() -> Any:
    """Lazy load web search provider."""
    try:
        from app.infrastructure.providers.web_search import MultiEngineSearchProvider
        return MultiEngineSearchProvider()
    except Exception as exc:
        logger.warning("MultiEngineSearchProvider unavailable: %s", exc, exc_info=True)
        return None


class Providers:
    """Providers bundle with lazy loading."""

    _news_provider: Any | None = None
    _quote_gateway: Any | None = None
    _web_search_provider: Any | None = None

    @property
    def news_provider(self) -> Any:
        if self._news_provider is None:
            self._news_provider = _lazy_news_provider()
        return self._news_provider

    @property
    def quote_gateway(self) -> Any:
        if self._quote_gateway is None:
            self._quote_gateway = _lazy_quote_gateway()
        return self._quote_gateway

    @property
    def web_search_provider(self) -> Any:
        if self._web_search_provider is None:
            self._web_search_provider = _lazy_web_search_provider()
        return self._web_search_provider


def create_providers() -> Providers:
    """Create providers bundle with lazy loading support."""
    return Providers()


def create_market_data_provider():
    """Process singleton market data provider (infrastructure only)."""
    from app.infrastructure.providers.market_data import MultiSourceMarketProvider

    return MultiSourceMarketProvider()


def create_tdx_local_file_port():
    """Process singleton TDX local file port (infrastructure only)."""
    from app.infrastructure.adapters.tdx_local_file_port_adapter import TdxLocalFilePortAdapter

    return TdxLocalFilePortAdapter()


def create_pytdx_market_port():
    """Process singleton Pytdx market port (infrastructure only)."""
    from app.infrastructure.adapters.pytdx_market_port_adapter import PytdxMarketPortAdapter

    return PytdxMarketPortAdapter()


def create_cn_fundamentals_port():
    from app.infrastructure.adapters.cn_fundamentals_port_adapter import CnFundamentalsPortAdapter

    return CnFundamentalsPortAdapter()


def create_cn_sector_board_port():
    from app.infrastructure.adapters.cn_sector_board_port_adapter import CnSectorBoardPortAdapter

    return CnSectorBoardPortAdapter()


def create_news_provider():
    from app.infrastructure.providers.news import AkshareNewsProvider

    return AkshareNewsProvider()


def create_ta_indicator_provider():
    from app.infrastructure.providers.indicators import TaIndicatorProvider

    return TaIndicatorProvider()


def create_cn_tdx_gpcw_provider(*, tdx_root_path: str):
    from app.infrastructure.providers.cn_tdx_gpcw import CnTdxGpcwProvider

    return CnTdxGpcwProvider(tdx_root_path=tdx_root_path)


def create_default_strategy_provider(market_provider):
    from app.infrastructure.providers.strategies import DefaultStrategyProvider

    return DefaultStrategyProvider(market_provider=market_provider)


def create_default_backtest_provider():
    from app.infrastructure.providers.strategies import DefaultBacktestProvider

    return DefaultBacktestProvider()


def create_backtest_engine():
    from app.infrastructure.providers.backtest_engine import BacktestEngine

    return BacktestEngine()


def bind_async_market_helpers_impl():
    from app.infrastructure.providers.async_market_provider import (
        get_async_market_provider,
        to_async_provider,
    )

    return to_async_provider, get_async_market_provider


def create_quote_cache_port():
    from app.infrastructure.adapters.quote_cache_port_adapter import QuoteCachePortAdapter

    return QuoteCachePortAdapter()


def create_cache_port():
    from app.infrastructure.cache.cache_manager import get_cache_manager
    from app.infrastructure.cache.cache_port_adapter import CacheManagerAdapter

    return CacheManagerAdapter(get_cache_manager())


def create_longhu_mapping_port():
    from app.infrastructure.adapters.longhu_mapping_port_adapter import LonghuMappingPortAdapter

    return LonghuMappingPortAdapter()


def create_data_quality_port():
    from app.infrastructure.adapters.data_quality_port_adapter import DataQualityPortAdapter

    return DataQualityPortAdapter()


def create_config_loader_port():
    from app.infrastructure.adapters.config_loader_port_adapter import ConfigLoaderPortAdapter

    return ConfigLoaderPortAdapter()


def create_longhu_ingestor():
    from app.infrastructure.adapters.market_ingestion.longhu_adapter import LonghuIngestorAdapter

    return LonghuIngestorAdapter()


def create_qlib_data_adapter(data_access, **kwargs):
    from app.infrastructure.qlib.data_adapter import QlibDataAdapter

    return QlibDataAdapter(data_access, **kwargs)


def create_qlib_bin_dumper_port():
    from app.infrastructure.adapters.qlib_bin_dumper_port_adapter import QlibBinDumperPortAdapter

    return QlibBinDumperPortAdapter()


def create_qlib_task_service_impl():
    from app.infrastructure.qlib.qlib_task_service import create_qlib_task_service

    return create_qlib_task_service()


def create_rdagent_job_store_port(base_dir):
    from app.infrastructure.adapters.rdagent_port_adapters import RDAgentJobStorePortAdapter

    return RDAgentJobStorePortAdapter(base_dir)


def create_rdagent_artifact_registry_port(base_dir):
    from app.infrastructure.adapters.rdagent_port_adapters import RDAgentArtifactRegistryPortAdapter

    return RDAgentArtifactRegistryPortAdapter(base_dir)


def create_rdagent_validation_port():
    from app.infrastructure.adapters.rdagent_port_adapters import RDAgentValidationPortAdapter

    return RDAgentValidationPortAdapter()


def create_pre_trade_validation_port():
    from app.infrastructure.adapters.pre_trade_validation_port_adapter import PreTradeValidationPortAdapter

    return PreTradeValidationPortAdapter(max_trade_amount=1_000_000.0)


def create_default_risk_preflight_impl():
    from app.infrastructure.risk.risk_gateway import DefaultRiskPreFlight

    return DefaultRiskPreFlight()


def create_default_position_sizing_impl():
    from app.infrastructure.risk.risk_gateway import DefaultPositionSizing

    return DefaultPositionSizing()


def create_tdx_finance_port():
    from app.infrastructure.adapters.tdx_finance_port_adapter import TdxFinancePortAdapter

    return TdxFinancePortAdapter()


def create_event_store_impl():
    from app.infrastructure.events.event_store import get_event_store

    return get_event_store()


def create_integration_events_impl():
    from app.infrastructure.events.integration_events import get_integration_events

    return get_integration_events()


def create_task_message_store_impl():
    from app.infrastructure.messaging.task_message_store import get_task_message_store

    return get_task_message_store()


def create_swarm_orchestrator_port():
    from app.infrastructure.agent.swarm_orchestrator_adapter import SwarmOrchestratorAdapter

    return SwarmOrchestratorAdapter()


def create_expert_skill_port():
    from app.infrastructure.agent.expert_skill_adapter import ExpertSkillAdapter

    return ExpertSkillAdapter()


def create_default_experiment_repository_impl():
    from pathlib import Path

    from app.config import BASE_DIR
    from app.infrastructure.agent.repositories.experiment_repository import ExperimentRepository

    return ExperimentRepository(Path(BASE_DIR) / "instance" / "agents" / "experiments")


def create_default_swarm_runtime_impl():
    from pathlib import Path

    from app.config import BASE_DIR
    from app.infrastructure.agent.swarm.runtime import SwarmRuntime
    from app.infrastructure.agent.swarm.store import SwarmStore

    storage_dir = Path(BASE_DIR) / "instance" / "agents" / "swarms" / "runs"
    return SwarmRuntime(SwarmStore(storage_dir))


def create_in_memory_task_pipeline():
    from app.infrastructure.task_pipeline.dag_tracker import InMemoryTaskPipeline

    return InMemoryTaskPipeline()


def create_task_observer_adapter(tracker):
    from app.infrastructure.task_pipeline.dag_tracker import TaskObserverAdapter

    return TaskObserverAdapter(tracker)


def create_shared_memory_manager():
    from app.infrastructure.memory.arrow_pool import get_global_memory_manager

    return get_global_memory_manager()


def create_default_walk_forward_optimizer():
    from app.infrastructure.strategy.walk_forward import DefaultWalkForwardOptimizer

    return DefaultWalkForwardOptimizer()


def create_markowitz_optimizer():
    from app.infrastructure.portfolio.optimizer import MarkowitzOptimizer

    return MarkowitzOptimizer()


def create_black_litterman_optimizer():
    from app.infrastructure.portfolio.optimizer import BlackLittermanOptimizer

    return BlackLittermanOptimizer()


def create_default_attribution_analysis():
    from app.infrastructure.portfolio.optimizer import DefaultAttributionAnalysis

    return DefaultAttributionAnalysis()


def create_data_infrastructure_quality_monitor():
    from app.config import get_settings
    from app.infrastructure.data_truth.unified_data_truth import UnifiedDataTruth

    settings = get_settings()
    return UnifiedDataTruth(tdx_root=getattr(settings, "tdx_root_path", None))


def create_data_lineage_tracker_port():
    from app.infrastructure.adapters.data_lineage_port_adapter import DataLineagePortAdapter

    return DataLineagePortAdapter()


def create_ai_analysis_adapter():
    from app.infrastructure.adapters.ai_analysis_port_adapter import AiAnalysisPortAdapter

    return AiAnalysisPortAdapter()


def create_ollama_prompt_adapter():
    from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter

    return OllamaPromptAdapter()


def create_trading_agents_research_port(*, fingpt_application_service=None):
    from app.infrastructure.adapters.trading_agents_research_adapter import (
        create_trading_agents_research_adapter,
    )

    return create_trading_agents_research_adapter(
        fingpt_application_service=fingpt_application_service,
    )
