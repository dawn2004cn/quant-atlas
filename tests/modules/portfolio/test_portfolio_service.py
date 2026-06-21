"""PortfolioApplicationService core path tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.dto.portfolio_dto import (
    OptimizationRequestDTO,
    PortfolioPositionDTO,
    PortfolioSnapshotDTO,
)
from app.domain.enums import MarketCode
from app.modules.portfolio_risk.services.portfolio_service import PortfolioApplicationService


def _quote(code: str, price: float = 10.0, prev_close: float | None = None, amplitude: float = 2.0):
    return SimpleNamespace(
        code=code,
        price=price,
        prev_close=prev_close if prev_close is not None else price * 0.98,
        amplitude=amplitude,
    )


@pytest.fixture
def portfolio_svc():
    provider = SimpleNamespace(
        get_realtime_quotes=lambda symbols, market: [_quote(s) for s in symbols],
        get_stock_history=lambda symbol, market, start, end: [
            {"close": 100.0},
            {"close": 105.0},
        ],
    )
    optimizer = SimpleNamespace(
        optimize=lambda assets, method, target_return, risk_aversion: SimpleNamespace(
            optimal_weights={"600519": 0.6, "000001": 0.4},
            expected_return=0.12,
            volatility=0.18,
            sharpe_ratio=0.55,
            method=method,
        ),
        compute_frontier=lambda assets, n_points: [
            SimpleNamespace(expected_return=0.1, volatility=0.15, sharpe_ratio=0.5)
        ],
    )
    attribution = SimpleNamespace(
        decompose=lambda **kwargs: {
            "total_return": kwargs["portfolio_return"],
            "alpha": kwargs.get("alpha", 0.0),
            "beta_timing": 0.01,
            "style_selection": 0.02,
            "residual": 0.0,
            "interpretation": "ok",
        }
    )
    return PortfolioApplicationService(
        market_provider=provider,
        optimizer=optimizer,
        attribution=attribution,
    )


def test_get_portfolio_snapshot_builds_positions(portfolio_svc):
    snapshot = portfolio_svc.get_portfolio_snapshot(
        symbols=["600519", "000001"],
        holdings={"600519": 100, "000001": 200},
        cash=50000.0,
    )
    assert snapshot.cash == 50000.0
    assert len(snapshot.positions) == 2
    assert snapshot.total_value > snapshot.cash


def test_check_rebalance_alerts_flags_deviation(portfolio_svc):
    snapshot = PortfolioSnapshotDTO(
        portfolio_id="default",
        total_value=100000,
        cash=0,
        positions=[
            PortfolioPositionDTO(
                symbol="600519",
                shares=100,
                current_price=10.0,
                current_value=1000.0,
                target_weight=0.05,
                current_weight=0.20,
                weight_deviation=0.15,
                unrealized_pnl=0.0,
                return_pct=0.0,
            ),
        ],
    )
    alerts = portfolio_svc.check_rebalance_alerts(
        snapshot,
        target_weights={"600519": 0.05},
        threshold=0.05,
    )
    assert len(alerts) == 1
    assert alerts[0].symbol == "600519"
    assert alerts[0].action == "减持"


def test_optimize_portfolio_delegates_to_optimizer(portfolio_svc):
    result = portfolio_svc.optimize_portfolio(
        OptimizationRequestDTO(symbols=["600519", "000001"], method="markowitz")
    )
    assert result.optimal_weights["600519"] == pytest.approx(0.6)
    assert result.expected_return == pytest.approx(0.12)
    assert len(result.frontier) == 1


def test_remember_rebalance_lesson_without_memory(portfolio_svc):
    result = portfolio_svc.remember_rebalance_lesson(
        symbol="600519",
        weights_before={"600519": 0.5},
        weights_after={"600519": 0.4},
        description="trim",
        score=0.8,
    )
    assert result["ok"] is False
    assert result["error"] == "local_memory_unavailable"
