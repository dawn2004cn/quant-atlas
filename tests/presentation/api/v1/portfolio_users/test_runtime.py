"""Tests for portfolio user runtime."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import PortfolioUserRouteDeps
from app.presentation.api.v1.portfolio_users.runtime import PortfolioUserRuntime, SimpleRateLimiter


def test_simple_rate_limiter_blocks_after_max():
    limiter = SimpleRateLimiter(window=60, max_attempts=2)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False


def test_require_ok_raises():
    deps = PortfolioUserRouteDeps(
        watchlist_service=object(),
        stock_group_service=object(),
        market_service=None,
        user_service=object(),
        audit_trail_service=None,
        enable_legacy_response_fields=True,
    )
    runtime = PortfolioUserRuntime(ctx=None, deps=deps)
    with pytest.raises(ValidationError, match="operation_failed"):
        runtime.require_ok(False, "nope")
