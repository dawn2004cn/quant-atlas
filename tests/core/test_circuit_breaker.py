"""Unit tests for CircuitBreaker — external API resilience pattern.

Covers app/core/circuit_breaker.py state machine:
  CLOSED → (failures ≥ threshold) → OPEN → (timeout) → HALF_OPEN → (successes ≥ threshold) → CLOSED
plus: shadow probe recovery, call_with_fallback, excluded exceptions,
adaptive tuning, decorator, and registry.
"""

from __future__ import annotations

import time

import pytest

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)


def _config(
    *, failure_threshold: int = 3, success_threshold: int = 2, timeout: float = 30.0,
    excluded: tuple = (),
) -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        excluded_exceptions=excluded,
    )


@pytest.fixture
def breaker() -> CircuitBreaker:
    return CircuitBreaker("test_svc", _config(failure_threshold=3, success_threshold=2))


# --- CLOSED → OPEN ----------------------------------------------------------


def test_starts_closed(breaker: CircuitBreaker):
    assert breaker.state.name == "CLOSED"


def test_opens_after_failure_threshold(breaker: CircuitBreaker):
    """Exactly failure_threshold failures transition CLOSED → OPEN."""
    for _ in range(3):
        breaker.record_failure(ValueError("boom"))
    assert breaker.state.name == "OPEN"


def test_stays_closed_below_threshold(breaker: CircuitBreaker):
    """Fewer than threshold failures keep it CLOSED."""
    breaker.record_failure(ValueError("x"))
    breaker.record_failure(ValueError("x"))
    assert breaker.state.name == "CLOSED"


# --- OPEN → HALF_OPEN (timeout) ---------------------------------------------


def test_transitions_to_half_open_after_timeout():
    """Once timeout elapses, state reports HALF_OPEN instead of OPEN."""
    b = CircuitBreaker("svc", _config(failure_threshold=1, timeout=0.05))
    b.record_failure(ValueError("down"))
    assert b.state.name == "OPEN"
    time.sleep(0.06)
    assert b.state.name == "HALF_OPEN"


def test_stays_open_before_timeout(breaker: CircuitBreaker):
    breaker.record_failure(ValueError("x"))
    breaker.record_failure(ValueError("x"))
    breaker.record_failure(ValueError("x"))
    assert breaker.state.name == "OPEN"


# --- HALF_OPEN → CLOSED (recovery) ------------------------------------------


def test_recovers_to_closed_after_successes():
    """success_threshold consecutive successes in HALF_OPEN close the circuit."""
    b = CircuitBreaker("svc", _config(failure_threshold=1, success_threshold=2, timeout=0.05))
    b.record_failure(ValueError("down"))
    time.sleep(0.06)
    assert b.state.name == "HALF_OPEN"
    b.record_success()
    b.record_success()
    assert b.state.name == "CLOSED"
    assert b._failure_count == 0


def test_half_open_failure_reopens():
    """A failure during HALF_OPEN sends it straight back to OPEN."""
    b = CircuitBreaker("svc", _config(failure_threshold=1, success_threshold=2, timeout=0.05))
    b.record_failure(ValueError("down"))
    time.sleep(0.06)
    assert b.state.name == "HALF_OPEN"
    b.record_failure(ValueError("still down"))
    assert b.state.name == "OPEN"


# --- call() semantics -------------------------------------------------------


def test_call_returns_result_when_closed(breaker: CircuitBreaker):
    assert breaker.call(lambda: 42) == 42


def test_call_raises_when_open(breaker: CircuitBreaker):
    for _ in range(3):
        breaker.record_failure(ValueError("x"))
    with pytest.raises(CircuitBreakerOpenError):
        breaker.call(lambda: 1)


def test_call_records_success(breaker: CircuitBreaker):
    breaker.call(lambda: "ok")
    breaker.call(lambda: "ok")
    assert breaker.state.name == "CLOSED"


def test_call_records_failure_and_propagates(breaker: CircuitBreaker):
    def boom():
        raise RuntimeError("fail")
    with pytest.raises(RuntimeError):
        breaker.call(boom)
    assert breaker._failure_count == 1


# --- call_with_fallback -----------------------------------------------------


def test_call_with_fallback_returns_value_on_success(breaker: CircuitBreaker):
    assert breaker.call_with_fallback(lambda: "result", fallback="default") == "result"


def test_call_with_fallback_returns_fallback_on_open(breaker: CircuitBreaker):
    for _ in range(3):
        breaker.record_failure(ValueError("x"))
    assert breaker.state.name == "OPEN"
    assert breaker.call_with_fallback(lambda: "real", fallback="fallback") == "fallback"


def test_call_with_fallback_returns_fallback_on_exception(breaker: CircuitBreaker):
    def boom():
        raise ValueError("nope")
    assert breaker.call_with_fallback(boom, fallback="safe") == "safe"


# --- Excluded exceptions ----------------------------------------------------


def test_excluded_exceptions_not_counted():
    """Exceptions in excluded_exceptions don't increment the failure count."""
    b = CircuitBreaker("svc", _config(failure_threshold=2, excluded=(KeyError,)))
    b.record_failure(KeyError("ignored"))
    b.record_failure(KeyError("ignored"))
    assert b.state.name == "CLOSED"
    assert b._failure_count == 0


# --- Shadow probe ------------------------------------------------------------


def test_shadow_probe_transitions_open_to_half_open():
    """A successful shadow probe moves OPEN → HALF_OPEN for recovery."""
    b = CircuitBreaker("svc", _config(failure_threshold=1, timeout=30.0))
    b.record_failure(ValueError("down"))
    assert b.state.name == "OPEN"
    b.register_shadow_probe(lambda: True)
    assert b.shadow_probe() is True
    assert b.state.name == "HALF_OPEN"


def test_shadow_probe_failure_keeps_open():
    """A failing shadow probe keeps the circuit OPEN."""
    b = CircuitBreaker("svc", _config(failure_threshold=1, timeout=30.0))
    b.record_failure(ValueError("down"))
    b.register_shadow_probe(lambda: (_ for _ in ()).throw(ConnectionError("still down")))
    assert b.shadow_probe() is False
    assert b.state.name == "OPEN"


def test_shadow_probe_without_function_returns_false():
    b = CircuitBreaker("svc", _config(failure_threshold=1))
    assert b.shadow_probe() is False


# --- Decorator --------------------------------------------------------------


def test_decorator_wraps_function():
    b = CircuitBreaker("svc", _config(failure_threshold=5))

    @b
    def echo(x):
        return x

    assert echo("hi") == "hi"


def test_decorator_blocks_when_open():
    b = CircuitBreaker("svc", _config(failure_threshold=1))
    for _ in range(1):
        b.record_failure(ValueError("x"))

    @b
    def fn():
        return "ok"

    with pytest.raises(CircuitBreakerOpenError):
        fn()


# --- Registry ----------------------------------------------------------------


def test_registry_returns_same_instance():
    a = CircuitBreakerRegistry.get("shared_svc")
    b = CircuitBreakerRegistry.get("shared_svc")
    assert a is b


def test_registry_status_includes_name():
    CircuitBreakerRegistry.get("status_svc")
    status = CircuitBreakerRegistry.get_all_status()
    assert "status_svc" in status
    assert status["status_svc"]["state"] == "closed"
