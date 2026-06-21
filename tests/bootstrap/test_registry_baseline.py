"""Baseline test: capture current registry state before migration."""
import pytest
from app.core.registry import registered_service_names


def test_baseline_registered_services():
    """Current: ~16 @register_service-decorated services from service_loader modules."""
    from app.bootstrap_components.service_loader import preload_service_modules

    preload_service_modules()

    names = registered_service_names()
    # Services registered via @register_service decorators in preloaded modules
    assert "gpcw_service" in names
    assert "data_infrastructure_service" in names
    assert "tdx_base_read_service" in names


def test_baseline_registered_factories():
    """register_factory entries exist after service_wiring import."""
    import sys

    if "app.bootstrap_components.service_wiring" not in sys.modules:
        __import__("app.bootstrap_components.service_wiring")

    from app.core.registry import get_registry

    names = set(get_registry().registered_names())
    assert "stock_service" in names
    assert "market_service" in names
    assert "ai_analysis_service" in names
