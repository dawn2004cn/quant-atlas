"""Explicit service wiring helpers (replaces ServiceLocator for bootstrap).


Migration path

--------------

Services tagged with ``@register_service`` (from ``app.core.registry``) are

automatically resolved by the registry.  The procedural ``wire_*`` functions

remain as fallbacks for services with complex wiring.

"""




from __future__ import annotations

import logging
from typing import Any

from app.core.typed_registry import TypedServiceRegistry, get_registry

# wire_* re-exports from dedicated wiring modules (context modules import from here)

logger = logging.getLogger(__name__)







def configure_service_registry(config: dict[str, Any] | None = None) -> TypedServiceRegistry:
    """Configure bootstrap registry with config (uses global singleton)."""
    from app.bootstrap_components.service_loader import preload_service_modules
    preload_service_modules()
    gr = get_registry()
    if hasattr(gr, '_config'):
        gr._config.update(config or {})
    else:
        gr._config = config or {}
    return gr







def _get_registry() -> TypedServiceRegistry:
    """Return the global bootstrap registry."""
    return get_registry()


def resolve_registry_session_factory(reg: Any) -> Any:
    """Resolve SQLAlchemy scoped_session factory for MySQL-backed repositories."""
    existing = getattr(reg, "_session_factory", None)
    if existing is not None and callable(existing):
        return existing

    from app.config import get_settings

    settings = get_settings()
    if not settings.use_mysql:
        return None

    try:
        from app.infrastructure.database.db_manager import get_db_manager

        sf = get_db_manager().get_session_factory(settings.mysql)
        reg._session_factory = sf
        return sf
    except Exception as exc:
        logger.warning("resolve_registry_session_factory failed: %s", exc)
        return None



# -- factory registrations (for complex service construction) --





def _make_stock_service(reg):

    from app.infrastructure.providers.news import AkshareNewsProvider
    from app.infrastructure.providers.rust_indicators import RustIndicatorProvider
    from app.infrastructure.repositories.deps import create_stock_cache
    from app.modules.market_data.services.stock_service import StockApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider



    return StockApplicationService(

        market_provider=get_market_data_provider(),

        indicator_provider=RustIndicatorProvider(),

        news_provider=AkshareNewsProvider(),

        stock_cache=create_stock_cache(),

    )



get_registry().register_factory("stock_service", _make_stock_service)





def _make_market_service(reg):

    from app.bootstrap_components.providers import create_cache_port
    from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider
    from app.infrastructure.repositories.deps import create_stock_cache
    from app.modules.market_data.services.market_service import MarketApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider



    return MarketApplicationService(

        get_market_data_provider(),

        CnIndustryProvider(),

        stock_cache=create_stock_cache(),

        cache=create_cache_port(),

    )



get_registry().register_factory("market_service", _make_market_service)


def _make_market_facade(reg):
    try:
        from app.application.facade import MarketFacade
        from app.infrastructure.providers.rust_indicators import RustIndicatorProvider
        from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
    except ImportError:
        logger.warning("MarketFacade import failed (circular import), skipping registration")
        return None

    indicator_provider = None
    try:
        indicator_provider = RustIndicatorProvider()
    except Exception:
        logger.warning("RustIndicatorProvider initialization failed", exc_info=True)
        indicator_provider = None

    return MarketFacade(
        stock_service=reg.get_or_none("stock_service"),
        market_service=reg.get_or_none("market_service"),
        watchlist_service=reg.get_or_none("watchlist_service"),
        market_data_provider=get_market_data_provider(),
        indicator_provider=indicator_provider,
    )


get_registry().register_factory("market_facade", _make_market_facade)


def _make_backtest_facade(reg):
    try:
        from app.application.facade import BacktestFacade
    except ImportError:
        logger.warning("BacktestFacade import failed (circular import), skipping registration")
        return None
    return BacktestFacade(strategy_service=reg.get_or_none("strategy_service"))


def _make_ai_facade(reg):
    try:
        from app.application.facade import AIFacade
    except ImportError:
        logger.warning("AIFacade import failed (circular import), skipping registration")
        return None
    return AIFacade(ai_analysis_service=reg.get_or_none("ai_analysis_service"))


get_registry().register_factory("ai_facade", _make_ai_facade)





def _make_basic_market_data_service(reg):
    from app.config import get_settings
    from app.infrastructure.repositories.common.deps import create_basic_market_data_repository
    from app.modules.data.services.basic_market_data_service import BasicMarketDataService

    repo = create_basic_market_data_repository(get_settings())
    # Pass telemetry=None to avoid AgentTelemetryService() auto-creation
    # which fails because the service resolver is not ready at factory time
    return BasicMarketDataService(repository=repo, telemetry=None)



get_registry().register_factory("basic_market_data_service", _make_basic_market_data_service)





def _make_global_market_service(reg):

    from app.modules.market_data.services.global_market_service import GlobalMarketService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider



    market_provider = get_market_data_provider()

    repository = None

    try:

        import os

        from app.config import BASE_DIR
        from app.infrastructure.repositories.sqlite.sqlite_openbb_repository import SQLiteOpenBBRepository

        db_path = os.path.join(str(BASE_DIR), "instance")

        repository = SQLiteOpenBBRepository(db_path=f"{db_path}/openbb_cache.db")

    except Exception:
        logger.warning("SQLiteOpenBBRepository initialization failed", exc_info=True)
        repository = None

    return GlobalMarketService(market_provider, repository)



get_registry().register_factory("global_market_service", _make_global_market_service)





def _make_ai_analysis_service(reg):

    from app.infrastructure.adapters.ai_analysis_port_adapter import AiAnalysisPortAdapter
    from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService



    stock = reg.get("stock_service")
    health_banner = reg.get_or_none("system_health_banner_service")

    return AiAnalysisService(
        stock_service=stock,
        ai_adapter=AiAnalysisPortAdapter(),
        system_health_banner_service=health_banner,
        parameter_store=reg.get_or_none("fast_path_parameter_store"),
        strategy_sop_service=reg.get_or_none("strategy_sop_service"),
    )



get_registry().register_factory("ai_analysis_service", _make_ai_analysis_service)





def _make_trade_plan_service(reg):

    from app.modules.execution.services.trade_plan_service import TradePlanService



    return TradePlanService(

        market_service=reg.get("market_service"),

        risk_service=reg.get_or_none("risk_service"),

    )



get_registry().register_factory("trade_plan_service", _make_trade_plan_service)





def _make_market_narrative_service(reg):

    from app.modules.market_data.services.market_narrative_service import MarketNarrativeService



    return MarketNarrativeService(

        market_service=reg.get("market_service"),

        ai_adapter=None,

    )



get_registry().register_factory("market_narrative_service", _make_market_narrative_service)





def _make_gpcw_service(reg):

    from app.modules.data.services.gpcw_service import GpcwApplicationService, _repository



    return GpcwApplicationService(repository=_repository())



get_registry().register_factory("gpcw_service", _make_gpcw_service)





def _make_industry_chain_service(reg):

    from app.modules.market_data.services.industry_chain_map_service import IndustryChainMapService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider



    return IndustryChainMapService(market_provider=get_market_data_provider())



get_registry().register_factory("industry_chain_service", _make_industry_chain_service)





def _make_data_infrastructure_service(reg):

    from app.modules.data.services.data_infrastructure_service import DataInfrastructureService



    ws_adapter = None

    try:

        from app.core.runtime_config import get_runtime_bool
        from app.infrastructure.realtime.socketio_websocket_adapter import SocketIOWebSocketAdapter



        if get_runtime_bool("ENABLE_SOCKETIO", False):

            ws_adapter = SocketIOWebSocketAdapter()

    except Exception:
        logger.warning("SocketIOWebSocketAdapter initialization failed", exc_info=True)
        ws_adapter = None

    return DataInfrastructureService(websocket=ws_adapter)



get_registry().register_factory("data_infrastructure_service", _make_data_infrastructure_service)





def _make_tdx_base_read_service(reg):

    from app.config import get_settings
    from app.modules.data.services.tdx_base_read_service import TdxBaseReadService



    return TdxBaseReadService(settings=get_settings())



get_registry().register_factory("tdx_base_read_service", _make_tdx_base_read_service)



# Services that must be resolved after bind_application_infrastructure().

_INFRA_REGISTRY_SERVICES: tuple[str, ...] = (

    "gpcw_service",

    "memory_optimization_service",

    "task_pipeline_service",

    "rdagent_run_service",

)





def rewire_infra_dependent_services(services: Any) -> None:

    """Clear and re-resolve registry services that depend on bound infrastructure."""

    for name in _INFRA_REGISTRY_SERVICES:

        if hasattr(services, name):

            setattr(services, name, None)

    _wire_from_registry(services)



# -- compat layer --





def _wire_from_registry(services: Any) -> None:

    """Resolve any ``@register_service``-decorated classes into *services*.



    Only sets attributes that are currently ``None``.

    """

    _get_registry().wire_to(services)


# Load factory registrations from domain wiring modules (side-effect imports).
def _preload_wiring_modules() -> None:
    """Import wiring modules so ``register_factory`` side effects run."""
    for module_name in (
        "app.bootstrap_components.wiring_market",
        "app.bootstrap_components.wiring_ai",
        "app.bootstrap_components.wiring_system",
        "app.bootstrap_components.wiring_trading",
        "app.bootstrap_components.wiring_data",
        "app.bootstrap_components.wiring_execution",
    ):
        try:
            __import__(module_name)
        except Exception:
            logger.warning("Wiring module preload failed: %s", module_name, exc_info=True)


_preload_wiring_modules()


def wire_recommendation_service(services: Any) -> None:
    """Resolve recommendation_service after dependent modules are wired."""
    reg = _get_registry()
    try:
        svc = reg.get_or_none("recommendation_service")
        if svc is None:
            svc = reg.get("recommendation_service")
    except Exception:
        logger.warning("recommendation_service resolution failed", exc_info=True)
        return
    if svc is not None:
        services.recommendation_service = svc
