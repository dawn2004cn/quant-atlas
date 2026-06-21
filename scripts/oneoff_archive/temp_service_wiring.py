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




from app.core.registry import ServiceRegistry, register_factory



logger = logging.getLogger(__name__)



_registry: ServiceRegistry | None = None





def configure_service_registry(config: dict[str, Any] | None = None) -> ServiceRegistry:

    """Create or replace the bootstrap ``ServiceRegistry`` with *config."""

    global _registry

    from app.bootstrap_components.service_loader import preload_service_modules



    preload_service_modules()

    _registry = ServiceRegistry(config=config or {})

    return _registry





def _get_registry() -> ServiceRegistry:

    global _registry

    if _registry is None:

        _registry = ServiceRegistry()

    return _registry



# -- factory registrations (for complex service construction) --





def _make_stock_service(reg):

    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    from app.modules.market_data.services.stock_service import StockApplicationService

    from app.infrastructure.providers.news import AkshareNewsProvider

    from app.infrastructure.providers.rust_indicators import RustIndicatorProvider

    from app.infrastructure.repositories.deps import create_stock_cache



    return StockApplicationService(

        market_provider=get_market_data_provider(),

        indicator_provider=RustIndicatorProvider(),

        news_provider=AkshareNewsProvider(),

        stock_cache=create_stock_cache(),

    )



register_factory("stock_service", _make_stock_service)





def _make_market_service(reg):

    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    from app.modules.market_data.services.market_service import MarketApplicationService

    from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider

    from app.infrastructure.repositories.deps import create_stock_cache



    return MarketApplicationService(

        get_market_data_provider(),

        CnIndustryProvider(),

        stock_cache=create_stock_cache(),

    )



register_factory("market_service", _make_market_service)





def _make_basic_market_data_service(reg):

    from app.modules.data.services.basic_market_data_service import BasicMarketDataService



    return BasicMarketDataService()



register_factory("basic_market_data_service", _make_basic_market_data_service)





def _make_global_market_service(reg):

    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    from app.modules.market_data.services.global_market_service import GlobalMarketService



    market_provider = get_market_data_provider()

    repository = None

    try:

        from app.infrastructure.repositories.sqlite.sqlite_openbb_repository import SQLiteOpenBBRepository

        import os

        from app.config import BASE_DIR

        db_path = os.path.join(str(BASE_DIR), "instance")

        repository = SQLiteOpenBBRepository(db_path=f"{db_path}/openbb_cache.db")

    except Exception:

        repository = None

    return GlobalMarketService(market_provider, repository)



register_factory("global_market_service", _make_global_market_service)





def _make_ai_analysis_service(reg):

    from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService

    from app.infrastructure.adapters.ai_analysis_port_adapter import AiAnalysisPortAdapter



    stock = reg.get("stock_service")

    return AiAnalysisService(
        stock_service=stock,
        ai_adapter=AiAnalysisPortAdapter(),
        system_health_banner_service=reg.get("system_health_banner_service"),
    )



register_factory("ai_analysis_service", _make_ai_analysis_service)





def _make_trade_plan_service(reg):

    from app.modules.execution.services.trade_plan_service import TradePlanService



    return TradePlanService(

        market_service=reg.get("market_service"),

        risk_service=reg.get_or_none("risk_service"),

    )



register_factory("trade_plan_service", _make_trade_plan_service)





def _make_market_narrative_service(reg):

    from app.modules.market_data.services.market_narrative_service import MarketNarrativeService



    return MarketNarrativeService(

        market_service=reg.get("market_service"),

        ai_adapter=None,

    )



register_factory("market_narrative_service", _make_market_narrative_service)





def _make_gpcw_service(reg):

    from app.modules.data.services.gpcw_service import GpcwApplicationService, _repository



    return GpcwApplicationService(repository=_repository())



register_factory("gpcw_service", _make_gpcw_service)





def _make_industry_chain_service(reg):

    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    from app.modules.market_data.services.industry_chain_map_service import IndustryChainMapService



    return IndustryChainMapService(market_provider=get_market_data_provider())



register_factory("industry_chain_service", _make_industry_chain_service)





def _make_data_infrastructure_service(reg):

    from app.modules.data.services.data_infrastructure_service import DataInfrastructureService



    ws_adapter = None

    try:

        from app.core.runtime_config import get_runtime_bool

        from app.infrastructure.realtime.socketio_websocket_adapter import SocketIOWebSocketAdapter



        if get_runtime_bool("ENABLE_SOCKETIO", False):

            ws_adapter = SocketIOWebSocketAdapter()

    except Exception:

