"""Portfolio route deps tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import (
    build_portfolio_route_deps,
    require_watchlist_for_portfolio,
)


def test_build_portfolio_route_deps_ok():
    portfolio = object()
    ctx = SimpleNamespace(
        market=None,
        portfolio_service=portfolio,
        watchlist_service=object(),
        market_service=object(),
        enable_legacy_response_fields=False,
    )
    deps = build_portfolio_route_deps(ctx)
    assert deps.portfolio_service is portfolio
    assert deps.watchlist_service is ctx.watchlist_service


def test_build_portfolio_route_deps_missing_portfolio_raises():
    ctx = SimpleNamespace(
        market=None,
        portfolio_service=None,
        watchlist_service=object(),
        market_service=None,
        enable_legacy_response_fields=True,
    )
    with pytest.raises(ValidationError, match="portfolio_service_unavailable"):
        build_portfolio_route_deps(ctx)


def test_require_watchlist_for_portfolio_raises_when_missing():
    deps = build_portfolio_route_deps(
        SimpleNamespace(
            market=None,
            portfolio_service=object(),
            watchlist_service=None,
            market_service=None,
            enable_legacy_response_fields=True,
        )
    )
    with pytest.raises(ValidationError, match="watchlist_service_unavailable"):
        require_watchlist_for_portfolio(deps)
