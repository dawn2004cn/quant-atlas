"""Legacy TDX adapter circuit breaker."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.middleware.degraded_context import clear_degraded_state, is_system_degraded
from app.infrastructure.adapters.legacy_tdx_adapter import LegacyTdxAdapter


@pytest.fixture(autouse=True)
def _clear_degraded():
    clear_degraded_state()
    yield
    clear_degraded_state()


def test_execute_returns_none_when_breaker_open():
    adapter = LegacyTdxAdapter()
    adapter._client = MagicMock()
    adapter._client.execute = MagicMock(return_value={"ok": True})
    adapter._breaker = MagicMock()
    adapter._breaker.call = MagicMock(side_effect=CircuitBreakerOpenError("open"))

    result = adapter.execute("get_security_list", 1)

    assert result is None
    assert is_system_degraded() is True
