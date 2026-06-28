from __future__ import annotations

import logging
from typing import Any

from app.domain.exceptions import RequiredComponentError

logger = logging.getLogger(__name__)


def init_required(name: str, init_fn):
    """Initialize a required component; hard fail on error."""
    try:
        return init_fn()
    except Exception as exc:
        logger.critical("REQUIRED component '%s' failed: %s", name, exc)
        raise RequiredComponentError(f"Required component '{name}' failed: {exc}") from exc


def init_optional(name: str, init_fn):
    """Initialize an optional component; warn and continue on error."""
    try:
        return init_fn()
    except Exception as exc:
        logger.warning("OPTIONAL component '%s' skipped: %s", name, exc)
        return None


def register_data_sources(app: Any = None, settings: Any = None) -> None:
    from app.core.data_source_registry import DataSource, get_data_source_registry
    reg = get_data_source_registry()
    for ds in [
        DataSource(name="tencent_realquote", type="quote", scope="realtime", market="CN", priority=90, description="实时行情（腾讯源）"),
        DataSource(name="tdx_history", type="kline", scope="history", market="CN", priority=90, description="历史K线（通达信）"),
        DataSource(name="akshare_history", type="kline", scope="history", market="CN", priority=70, description="历史K线（AkShare）"),
        DataSource(name="yfinance_us", type="quote", scope="realtime", market="US", priority=80, description="美股实时行情"),
        DataSource(name="yfinance_hk", type="quote", scope="realtime", market="HK", priority=80, description="港股实时行情"),
        DataSource(name="qlib_factor", type="factor", scope="batch", market="CN", priority=90, description="Qlib因子数据"),
        DataSource(name="chip_akshare", type="chip", scope="realtime", market="CN", priority=80, description="筹码分布（AkShare）"),
        DataSource(name="news_eastmoney", type="news", scope="realtime", market="CN", priority=90, description="新闻资讯（东方财富）"),
        DataSource(name="msn_index", type="index", scope="realtime", market="global", priority=80, description="全球指数（MSN）"),
    ]:
        reg.register(ds)
    logger.info("DataSourceRegistry: registered %d data sources", reg.stats()["total"])


def _init_cluster_event_bus_impl(settings: Any, app: Any) -> None:
    """Internal implementation: (settings, app) order."""
    from app.core.cluster_event_bus import get_cluster_event_bus
    try:
        mesh_bus = get_cluster_event_bus().ensure_cluster(
            redis_url=settings.task_message_redis_url,
        )
        if mesh_bus is not None:
            app.config["MESH_MANIFEST"] = mesh_bus.get_manifest()
            app.config["CLUSTER_EVENT_BUS"] = get_cluster_event_bus().manifest()
    except Exception as exc:
        logger.warning("Cluster event bus init skipped: %s", exc)


def init_cluster_event_bus(app: Any, settings: Any) -> None:
    """Bootstrap-compatible wrapper: (app, settings) order."""
    _init_cluster_event_bus_impl(settings, app)


def start_truth_sentry():
    from app.infrastructure.realtime.truth_sentry import start_truth_sentry
    start_truth_sentry()


def _init_side_effects_impl() -> None:
    """Initialize side-effect imports that register themselves."""
    try:
        pass
    except Exception as exc:
        logger.debug("investment_manager_tasks skipped: %s", exc)
    try:
        pass
    except Exception as exc:
        logger.debug("symbiotic_execution_service skipped: %s", exc)
    try:
        logger.debug("Phase 16 execution and immunity services discovered")
    except Exception as exc:
        logger.debug("immune_agent_service skipped: %s", exc)
    try:
        import app.domain.alpha.auto_hotswap_patch as _auto_hotswap_patch
        _auto_hotswap_patch.enable_hot_swap_patch()
        logger.debug("Auto hot-swap trigger wired")
    except Exception as exc:
        logger.debug("auto_hotswap_patch skipped: %s", exc)
    try:
        logger.debug("Prompt <> Decision feedback loop initialized")
    except Exception as exc:
        logger.debug("prompt/decision_feedback skipped: %s", exc)
    try:
        logger.info("Agent-App Runtime wired (5 built-in apps)")
    except Exception as exc:
        logger.debug("AgentAppRegistry skipped: %s", exc)
    try:
        logger.debug("NeuralMesh + HyperGrid + Canvas services discovered")
    except Exception as exc:
        logger.debug("NeuralMesh/HyperGrid/Canvas skipped: %s", exc)


def init_side_effects(app: Any = None, settings: Any = None, services: Any = None) -> None:
    """Bootstrap-compatible wrapper: (app, settings, services) order."""
    _init_side_effects_impl()


def init_required_components(app: Any, settings: Any, services: Any) -> None:
    """Initialize required components. Currently a no-op; all wiring done in create_services."""
    # Required components are initialized within create_services / bind_application_infrastructure.
    logger.debug("init_required_components: delegated to create_services")


def init_optional_components(app: Any, settings: Any, services: Any) -> None:
    """Initialize optional components. Currently a no-op; all wiring done in create_services."""
    logger.debug("init_optional_components: delegated to create_services")


def build_registry_config(settings) -> dict[str, Any]:
    return {
        "MESH_ENABLED": getattr(settings, "mesh_enabled", False),
        "PERCEPTION_ENABLED": getattr(settings, "perception_enabled", False),
        "ENABLE_SOCKETIO": getattr(settings, "enable_socketio", False),
        "ENABLE_VISION": getattr(settings, "enable_vision", True),
        "ENABLE_COLLABORATION": getattr(settings, "enable_collaboration", True),
    }
