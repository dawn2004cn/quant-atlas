from __future__ import annotations

"""TDX adapter with real TDX connection."""


import logging
from typing import Any

from app.core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)

logger = logging.getLogger(__name__)

# 导入真正的TDX连接管理器
try:
    from app.infrastructure.pytdx import TdxConnectionManager
except ImportError:
    TdxConnectionManager = None


class LegacyTdxAdapter:
    """Real TDX adapter using TdxConnectionManager."""

    def __init__(self) -> None:
        self._breaker = CircuitBreakerRegistry.get(
            "tdx_legacy",
            CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
        )
        self._client = self._build_client()

    def _build_client(self):
        """Build real TDX client using TdxConnectionManager."""
        if TdxConnectionManager is not None:
            try:
                return TdxConnectionManager()
            except Exception as e:
                logger.warning("LegacyTdxAdapter._build_client: %s", e)
                return None
        return None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    @property
    def is_connected(self) -> bool:
        if self._client is None:
            return False
        return bool(getattr(self._client, "is_connected", False))

    def reconnect(self) -> None:
        if self._client is None:
            return
        for name in ("reconnect", "_reconnect"):
            fn = getattr(self._client, name, None)
            if callable(fn):
                fn()
                return

    def execute(self, method: str, *args: Any) -> Any:
        if self._client is None:
            return None
        executor = getattr(self._client, "execute", None)
        if not callable(executor):
            return None
        try:
            return self._breaker.call(executor, method, *args)
        except CircuitBreakerOpenError:
            try:
                from app.core.middleware.degraded_context import mark_system_degraded

                mark_system_degraded("tdx_legacy")
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
            logger.warning("LegacyTdxAdapter circuit open; skip %s", method)
            return None
