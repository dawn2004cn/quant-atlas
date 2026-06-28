from __future__ import annotations

"""Tencent quote gateway adapter."""


import requests

from app.core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)


class TencentQuoteGateway:
    """HTTP adapter for Tencent quote endpoint."""

    def __init__(self) -> None:
        self._breaker = CircuitBreakerRegistry.get(
            "tencent_quotes",
            CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
        )

    def fetch_quotes_text(self, normalized_symbols: list[str], timeout: float) -> str:
        if not normalized_symbols:
            return ""
        try:
            return self._breaker.call(self._fetch, normalized_symbols, timeout)
        except CircuitBreakerOpenError:
            try:
                import logging

                from app.core.middleware.degraded_context import mark_system_degraded

                logger = logging.getLogger(__name__)

                mark_system_degraded("tencent_quotes")
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
            return ""

    def _fetch(self, normalized_symbols: list[str], timeout: float) -> str:
        response = requests.get(
            f"http://qt.gtimg.cn/q={','.join(normalized_symbols)}",
            timeout=timeout,
        )
        return response.text or ""
