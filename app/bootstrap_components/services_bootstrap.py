"""Service bootstrap utilities for decentralized initialization.

This module replaces the manual ``_try_init_*`` methods in ``services.py`` with a
dependency‑aware topological loader. All service initialization logic is moved
here to enable plugin‑style service registration.
"""

from __future__ import annotations

import logging
from typing import Any

from app.bootstrap_components.service_wiring import _get_registry

logger = logging.getLogger(__name__)


class ServiceBootstrap:
    """Topological service loader based on ``ServiceRegistry`` metadata.

    The loader walks the dependency graph declared via ``@register_service``
    (or ``register_factory``) and instantiates services in a safe order.
    """

    @staticmethod
    def load_services(services: Any) -> None:
        """Load all services into the given ``services`` instance.

        The algorithm uses Kahn's topological sort to respect ``depends``
        declarations. If a cycle is detected, a warning is logged and the
        remaining services are skipped.
        """
        registry = _get_registry()
        entries = registry.get_all_entries()

        # Build adjacency list and in‑degree map
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        for name, entry in entries.items():
            deps = entry.depends or []
            graph[name] = deps
            in_degree[name] = 0
        for name, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Queue of services with no remaining dependencies
        ready = [n for n, d in in_degree.items() if d == 0]
        loaded = set()

        while ready:
            current = ready.pop(0)
            if getattr(services, current, None) is not None:
                loaded.add(current)
                continue
            try:
                ServiceBootstrap._load_service(current, services)
                loaded.add(current)
            except Exception as exc:  # pragma: no cover  defensive
                logger.warning("Failed to load service %s: %s", current, exc)
                continue

            # Decrease in‑degree of dependents
            for dependent, deps in graph.items():
                if current in deps:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        ready.append(dependent)

        if len(loaded) != len(entries):
            missing = set(entries) - loaded
            logger.warning(
                "Possible circular dependency or missing prerequisites: %s",
                missing,
            )

    @staticmethod
    def _load_service(name: str, services: Any) -> None:
        """Instantiate a single service and attach it to ``services``.

        The registry may provide either a ``factory`` callable or a concrete
        class. The factory receives the ``ServiceRegistry`` instance so it can
        resolve further dependencies.
        """
        registry = _get_registry()
        entry = registry.get_entry(name)
        if not entry:
            logger.debug("Service %s not found in registry", name)
            return
        if entry.factory:
            instance = entry.factory(registry)
        else:
            instance = entry.cls()
        setattr(services, name, instance)
        logger.debug("Loaded service %s", name)


# ---------------------------------------------------------------------------
# Legacy init helpers  extracted verbatim from the original ``services.py``
# ---------------------------------------------------------------------------

def init_watchlist_services(services: Any, repositories: Any | None = None) -> None:
    """Initialize ``watchlist_service`` and ``stock_group_service``.

    This mirrors the former ``_try_init_watchlist_service`` and
    ``_try_init_stock_group_service`` logic.
    """
    if services.watchlist_service is not None and services.stock_group_service is not None:
        return
    try:
        from app.modules.market_data.services.watchlist_service import WatchlistApplicationService
        from app.modules.market_data.services.stock_group_service import StockGroupApplicationService
        from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
        from app.modules.market_data.services.watchlist_experience_service import WatchlistExperienceService

        watchlist_repo = getattr(repositories, "watchlist_repository", None) if repositories else None
        stock_group_repo = getattr(repositories, "stock_group_repository", None) if repositories else None

        if watchlist_repo and services.watchlist_service is None:
            services.watchlist_service = WatchlistApplicationService(
                repository=watchlist_repo,
                stock_group_repository=stock_group_repo,
            )

        if stock_group_repo and services.stock_group_service is None:
            services.stock_group_service = StockGroupApplicationService(repository=stock_group_repo)

        # Derivative services that depend on the two above
        if (
            services.watchlist_service
            and services.stock_group_service
            and services.market_service
            and services.stock_service
            and services.watchlist_agent_service is None
        ):
            services.watchlist_agent_service = WatchlistAgentService(
                market_service=services.market_service,
                stock_service=services.stock_service,
                watchlist_service=services.watchlist_service,
                stock_group_service=services.stock_group_service,
            )

        if services.watchlist_agent_service and services.watchlist_experience_service is None:
            services.watchlist_experience_service = WatchlistExperienceService(
                watchlist_agent_service=services.watchlist_agent_service,
            )
    except Exception as exc:  # pragma: no cover  defensive
        logger.warning("Could not initialize watchlist services: %s", exc)


def init_signal_flag_service(services: Any, settings: Any | None = None) -> None:
    """Initialize ``signal_flag_service``.

    Mirrors the original ``_try_init_signal_flag_service`` implementation.
    """
    if services.signal_flag_service is not None:
        return
    try:
        from app.config import get_settings
        from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
        from app.infrastructure.repositories.deps import create_signal_flag_pool_repository

        s = settings or get_settings()
        repo = create_signal_flag_pool_repository(s)
        services.signal_flag_service = SignalFlagScannerService(
            stock_service=services.stock_service,
            stock_cache=services._stock_cache,
            repository=repo,
            enable_qlib=False,
        )
    except Exception as exc:  # pragma: no cover  defensive
        logger.warning("Could not initialize signal_flag_service: %s", exc)


def init_user_services(services: Any, repositories: Any | None = None) -> None:
    """Initialize ``auth_service`` and ``user_service`` when a user repository is present."""
    if services.auth_service is not None and services.user_service is not None:
        return
    try:
        if repositories and getattr(repositories, "user_repository", None):
            from app.modules.user.services.user.auth_service import AuthService
            from app.modules.user.services.user.user_service import UserApplicationService

            services.auth_service = AuthService(user_repository=repositories.user_repository)
            services.user_service = UserApplicationService(
                repository=repositories.user_repository,
                auth_service=services.auth_service,
            )
    except Exception as exc:  # pragma: no cover  defensive
        logger.warning("Could not initialize user services: %s", exc)

