"""Services configuration."""

from __future__ import annotations

import logging
from typing import Any

from app.bootstrap_components.service_readiness import (
    resolve_all_critical_services,
    validate_service_readiness,
)
from app.modules.system.services.admin.admin_stock_service import configure_admin_stock_service

logger = logging.getLogger(__name__)


def create_services(
    settings: Any = None,
    repositories: Any = None,
    providers: Any = None,
    session_factory: Any = None,
    *,
    registry_config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Create services bundle via explicit wiring (no ServiceLocator scan)."""
    if registry_config is not None:
        from app.bootstrap_components.service_wiring import configure_service_registry
        configure_service_registry(registry_config)
    
    _repositories = repositories
    _settings = settings
    
    class Services:
        """Dynamic service container resolved by ServiceRegistry + factories.
        Eliminates the old 70+ explicit ``= None`` attributes.
        Each ``services.X`` access resolves lazily via:
        1. Direct attribute (set by wire/factory)
        2. ``ServiceRegistry`` for registered services
        3. ``None`` (graceful missing)
        """
        
        _repositories = None
        _settings = None
        _stock_cache = None
        
        def __init__(self):
            self._settings = _settings
            self._repositories = _repositories
            from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
            from app.bootstrap_components.module_wiring import initialize_all_modules
            from app.bootstrap_components.service_wiring import _get_registry, _wire_from_registry
            from app.config import get_settings
            from app.infrastructure.repositories.deps import create_stock_cache
            
            s = _settings or get_settings()
            self._stock_cache = create_stock_cache()
            bind_application_infrastructure(s)

            reg = _get_registry()
            from app.bootstrap_components.service_wiring import resolve_registry_session_factory

            reg._session_factory = session_factory or resolve_registry_session_factory(reg)

            _wire_from_registry(self)

            reg.wire_to(self)
            
            configure_admin_stock_service(self._stock_cache)
            
            _registry_config = {
                key: value
                for key, value in vars(s).items()
                if isinstance(value, (bool, int, float, str))
            }
            initialize_all_modules(self, session_factory=None, config=_registry_config)
            
            try:
                from app.bootstrap_components.service_wiring import wire_recommendation_service
                wire_recommendation_service(self)
            except Exception:
                logger.warning("Recommendation service wiring failed", exc_info=True)
            try:
                from app.bootstrap_components.wiring_optimization import wire_optimization_services
                wire_optimization_services(self)
            except Exception as exc:
                logger.debug("Optimization wiring skipped: %s", exc)
            
            try:
                from app.bootstrap_components.wiring_execution import wire_execution_fast_path
                wire_execution_fast_path()
            except Exception as exc:
                logger.warning("Execution FastPath wiring failed: %s", exc)
                
            # Wire Strategy SOP Service (Cognitive Governance)
            try:
                from app.bootstrap_components.wiring_strategy import wire_strategy_sop
                wire_strategy_sop()
            except Exception as exc:
                logger.warning("Strategy SOP wiring failed: %s", exc)
                
            self._eager_resolve_required(reg)
            validate_service_readiness(self)
            try:
                resolve_all_critical_services(reg)
            except Exception:
                logger.error("Critical service resolution failed", exc_info=True)
                raise
        
        def _eager_resolve_required(self, reg: Any) -> None:
            """Materialize REQUIRED services on the container (fail loudly in logs)."""
            from app.bootstrap_components.service_readiness import REQUIRED_SERVICE_ATTRS

            for name in REQUIRED_SERVICE_ATTRS:
                if self.__dict__.get(name) is not None:
                    continue
                try:
                    instance = reg.resolve(name)
                except Exception:
                    logger.warning(
                        "Eager resolve failed for required service %s",
                        name,
                        exc_info=True,
                    )
                    continue
                if instance is not None:
                    object.__setattr__(self, name, instance)
        
        def __getattr__(self, name: str) -> Any:
            """Lazy resolution via ServiceRegistry."""
            if name.startswith("_"):
                raise AttributeError(name)
            try:
                from app.bootstrap_components.service_wiring import _get_registry
                val = _get_registry().get_or_none(name)
                if val is not None:
                    object.__setattr__(self, name, val)
                    return val
            except Exception:
                logger.warning("Service resolution failed for '%s'", name, exc_info=True)
            return None
        
        def get(self, name: str, default: Any = None) -> Any:
            """Explicit lookup for programmatic access."""
            return getattr(self, name, default)
    
    return Services()
