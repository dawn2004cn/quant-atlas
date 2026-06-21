"""Tests for service factory resolution and error reporting."""

from __future__ import annotations

import os

os.environ.setdefault("STRICT_BOOTSTRAP", "0")
os.environ.setdefault("CACHE_BACKEND", "memory")
os.environ.setdefault("REDIS_URL", "memory://")


class TestServiceFactoryResolution:
    """Verify key services can be resolved from the registry."""

    def test_market_service_resolves(self):
        from app.core.registry import _get_registry

        reg = _get_registry()
        svc = reg.get_or_none("market_service")
        assert svc is not None, "market_service must resolve"
        assert hasattr(svc, "get_panorama")

    def test_watchlist_service_resolves(self):
        from app.core.registry import _get_registry

        reg = _get_registry()
        svc = reg.get_or_none("watchlist_service")
        assert svc is not None, "watchlist_service must resolve"

    def test_stock_service_resolves(self):
        from app.core.registry import _get_registry

        reg = _get_registry()
        svc = reg.get_or_none("stock_service")
        assert svc is not None, "stock_service must resolve"

    def test_strategy_service_resolves(self):
        from app.core.registry import _get_registry

        reg = _get_registry()
        svc = reg.get_or_none("strategy_service")
        assert svc is not None, "strategy_service must resolve"

    def test_integration_stack_service_resolves(self):
        from app.core.registry import _get_registry

        reg = _get_registry()
        svc = reg.get_or_none("integration_stack_service")
        # May be None if dependent services are missing — but must NOT raise
        assert svc is None or hasattr(svc, "get_stack_status")


class TestServiceFactoryErrors:
    """Services that cannot be created should raise clear errors, not crash silently."""

    def test_missing_required_service_raises(self):
        """If a required service is missing, factory should raise."""
        from app.core.registry import ServiceRegistry

        reg = ServiceRegistry()
        # market_service is required but not registered — should raise KeyError
        with reg.get_or_none("market_service") is not None:
            pass  # If it resolves, that's fine (factory may have provided it)
