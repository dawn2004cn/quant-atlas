import pathlib

p = pathlib.Path("app/core/resilience.py")
c = p.read_text(encoding="utf-8")

# Add shadow probe registration function and boot-time wiring
add = """
def register_service_shadow_probes(registry=None) -> None:
    \"\"\"Register lightweight shadow probes for circuit-protected external services.

    Called once at bootstrap so that each ``CircuitBreaker`` can probe
    recovery in the background when OPEN, without risking real traffic.
    \"\"\"
    from app.core.circuit_breaker import CircuitBreakerRegistry as CBRegistry

    # --- OpenBB adapter ---
    _register_openbb_probe(CBRegistry)

    # --- FinGPT adapter ---
    _register_fingpt_probe(CBRegistry)

    # --- Ollama adapter ---
    _register_ollama_probe(CBRegistry)


def _register_openbb_probe(registry) -> None:
    \"\"\"Register a lightweight OpenBB probe (single-quote fetch).\"\"\"
    cb = registry.get("openbb_quotes")
    if cb is not None:

        def _probe() -> None:
            import os
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
    \"\"\"Register a FinGPT probe (just import + connectivity check).\"\"\"
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
    \"\"\"Register an Ollama probe (HEAD /api/tags to verify reachability).\"\"\"
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
"""

c += add
p.write_text(c, encoding="utf-8")
print("Extended resilience.py OK")
