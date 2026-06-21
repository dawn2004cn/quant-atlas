"""Portfolio user route deps tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import build_portfolio_user_route_deps


def test_build_portfolio_user_route_deps_requires_watchlist():
    ctx = SimpleNamespace(
        market=None,
        watchlist_service=object(),
        stock_group_service=object(),
        market_service=None,
        user_service=None,
        user_audit_trail_service=None,
        enable_legacy_response_fields=True,
    )
    deps = build_portfolio_user_route_deps(ctx)
    assert deps.watchlist_service is ctx.watchlist_service
    assert deps.stock_group_service is ctx.stock_group_service


def test_build_portfolio_user_route_deps_missing_watchlist_raises():
    ctx = SimpleNamespace(
        market=None,
        watchlist_service=None,
        stock_group_service=object(),
        market_service=None,
        user_service=None,
        user_audit_trail_service=None,
        enable_legacy_response_fields=True,
    )
    with pytest.raises(ValidationError, match="watchlist_service_unavailable"):
        build_portfolio_user_route_deps(ctx)
