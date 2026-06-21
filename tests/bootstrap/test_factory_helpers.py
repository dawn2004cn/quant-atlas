"""Tests for bootstrap factory_helpers."""

from __future__ import annotations

from app.bootstrap_components.factory_helpers import zero_arg_service


def test_zero_arg_service_instantiates_circuit_breaker_registry():
    factory = zero_arg_service("app.core.circuit_breaker", "CircuitBreakerRegistry")
    instance = factory(None)
    assert instance.__class__.__name__ == "CircuitBreakerRegistry"
