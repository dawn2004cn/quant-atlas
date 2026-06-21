"""Tencent quote gateway circuit breaker."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.middleware.degraded_context import clear_degraded_state, is_system_degraded
from app.infrastructure.adapters.tencent_quote_gateway import TencentQuoteGateway


@pytest.fixture(autouse=True)
def _clear_degraded():
    clear_degraded_state()
    yield
    clear_degraded_state()


def test_fetch_quotes_text_returns_empty_when_breaker_open():
    gateway = TencentQuoteGateway()
    gateway._breaker = MagicMock()
    gateway._breaker.call = MagicMock(side_effect=CircuitBreakerOpenError("open"))

    result = gateway.fetch_quotes_text(["sh600519"], timeout=2.0)

    assert result == ""
    assert is_system_degraded() is True
