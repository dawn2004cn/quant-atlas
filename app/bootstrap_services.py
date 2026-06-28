
from __future__ import annotations

"""Service?layer bootstrap ? builds the TypedServiceRegistry, wires all services,
and returns a ready?to?use ``Services`` container.

All Flask?related code lives in ``bootstrap_app.py``; this module is pure Python
and can be unit?tested without a web server.
"""

import logging
from typing import Any

from app.bootstrap_components.service_wiring import _get_registry, _wire_from_registry, configure_service_registry
from app.config import get_settings

logger = logging.getLogger(__name__)

def create_services(
    settings: Any | None = None,
    repositories: Any | None = None,
    providers: Any | None = None,
    session_factory: Any | None = None,
    *,
    registry_config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Create the services bundle.

    * ``settings`` ? optional pre?built :class:`AppSettings`. If ``None`` we call
      :func:`app.config.get_settings`.
    * ``repositories`` / ``providers`` ? rarely used legacy hooks ? kept for
      backward compatibility.
    * ``registry_config`` ? allows external code to pre?register extra services
      before the standard wiring runs.
    """
    if registry_config is not None:
        configure_service_registry(registry_config)

    _settings = settings or get_settings()
    _repositories = repositories

    class Services:
        """Dynamic container ? attribute access resolves via the registry.

        The original ``create_services`` injected a handful of attributes
        (e.g. ``_stock_cache``). Those are now lazily provided by the registry.
        """

        _settings = None
        _repositories = None
        _stock_cache = None

        def __init__(self):
            self._settings = _settings
            self._repositories = _repositories

            # Bind the low?level infrastructure (DB, cache, etc.)
            from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
            from app.config import get_settings
            from app.infrastructure.repositories.deps import create_stock_cache

            s = _settings or get_settings()
            self._stock_cache = create_stock_cache()
            bind_application_infrastructure(s)

            # Wire all factories / services into *this* container
            _wire_from_registry(self)

            # Attach the global registry to the container for advanced use?cases
            reg = _get_registry()
            reg._session_factory = session_factory
            reg.wire_to(self)

            # Example of a post?wiring hook ? kept for backward compatibility
            try:
                from app.bootstrap_components.service_wiring import wire_recommendation_service
                wire_recommendation_service(self)
            except Exception as exc:  # pragma: no cover ? optional feature
                logger.debug("Recommendation service not available: %s", exc)

            try:
                from app.bootstrap_components.wiring_optimization import wire_optimization_services
                wire_optimization_services(self)
            except Exception as exc:  # pragma: no cover ? optional feature
                logger.debug("Optimization services not available: %s", exc)

        # The ``__getattr__`` fallback lives in ``app.core.registry`` ? no need to duplicate it here.

    return Services()
