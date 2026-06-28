"""Resilience tools for infrastructure protection.

Unified on ``app.core.circuit_breaker`` as the canonical implementation.
"""

import functools
from typing import Any

from app.core.circuit_breaker import (
    CircuitBreaker as _CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry as _Registry,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Adapter wrapping the canonical ``CircuitBreaker`` for backward compat."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        c = config or CircuitBreakerConfig()
        self._breaker = _CircuitBreaker(name, c)

    @property
    def is_available(self) -> bool:
        return self._breaker.state.value == "closed"

    @property
    def status(self) -> str:
        return self._breaker.state.value

    def record_failure(self, exc: Exception) -> None:
        self._breaker.record_failure(exc)


class CircuitBreakerRegistry:
    """Adapter wrapping the canonical registry."""

    def __init__(self):
        self._delegate = _Registry()

    def get_breaker(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        self._delegate.get(name)
        return CircuitBreaker(name)


_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    return _registry


# Global circuit breaker for external data sources
data_source_breaker = _CircuitBreaker("data_source")


def protected_loader(func):
    """Decorator to apply circuit breaker to data loaders."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return data_source_breaker.call(func, *args, **kwargs)
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker tripped: returning empty/fallback data.")
            return {}

    return wrapper

def register_service_shadow_probes(registry=None) -> None:
    """Register lightweight shadow probes for circuit-protected external services.

    Called once at bootstrap so that each ``CircuitBreaker`` can probe
    recovery in the background when OPEN, without risking real traffic.
    """
    from app.core.circuit_breaker import CircuitBreakerRegistry as CBRegistry

    # --- OpenBB adapter ---
    _register_openbb_probe(CBRegistry)

    # --- FinGPT adapter ---
    _register_fingpt_probe(CBRegistry)

    # --- Ollama adapter ---
    _register_ollama_probe(CBRegistry)


def _register_openbb_probe(registry) -> None:
    """Register a lightweight OpenBB probe (single-quote fetch)."""
    cb = registry.get("openbb_quotes")
    if cb is not None:

        def _probe() -> None:
            try:
                from openbb import obb
            except ImportError:
                raise RuntimeError("openbb not installed")
            # Ping via a cheap profile check on a known symbol
            try:
                obb.equity.price.quote(symbol="000001.SZ", provider="yfinance")
            except Exception:
                # fallback: just check import worked
                pass

        cb.register_shadow_probe(_probe)

    for name in ("openbb_profile", "openbb_history"):
        cb = registry.get(name)
        if cb is not None:
            cb.register_shadow_probe(_probe)


def _register_fingpt_probe(registry) -> None:
    """Register a FinGPT probe (just import + connectivity check)."""
    cb = registry.get("fingpt_sentiment")
    if cb is not None:

        def _probe() -> None:
            # FinGPT relies on the LLM being reachable.
            from app.infrastructure.adapters.fingpt_adapter import SimpleFinGPTAdapter
            # Instantiate a minimal check; no real text is sent.
            adapter = SimpleFinGPTAdapter()
            if adapter._llm is None:
                raise RuntimeError("FinGPT LLM not configured")

        cb.register_shadow_probe(_probe)


def _register_ollama_probe(registry) -> None:
    """Register an Ollama probe (HEAD /api/tags to verify reachability)."""
    cb = registry.get("ollama_generate")
    if cb is not None:

        def _probe() -> None:
            import requests
            from app.core.config import get_settings
            s = get_settings()
            base = getattr(s, "OLLAMA_BASE_URL", "http://localhost:11434")
            resp = requests.get(f"{base.rstrip('/')}/api/tags", timeout=5)
            resp.raise_for_status()

        cb.register_shadow_probe(_probe)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "register_service_shadow_probes",
]
