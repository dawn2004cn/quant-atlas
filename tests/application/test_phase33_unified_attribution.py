"""Phase 33 UX-1: unified attribution report."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService


def test_build_report_returns_extended_dto_fields() -> None:
    service = UnifiedAttributionService()
    report = service.build_report(
        strategy_name="demo",
        period="30d",
        positions=[
            {"symbol": "600519", "name": "茅台", "value": 100000, "return_pct": 2.0, "sector": "白酒"},
        ],
        benchmark_return=1.0,
        factor_exposures={"momentum": 0.2},
        factor_returns={"momentum": 0.05},
        alpha=0.01,
        include_slippage=False,
    )
    assert report.strategy_name == "demo"
    assert report.market_effect.alpha is not None
    assert len(report.style_contributions) >= 4
    assert report.summary


def test_build_report_merges_slippage_when_mysql(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.use_mysql = True
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    slippage_service = MagicMock()
    slippage_service.analyze_slippage = AsyncMock(
        return_value={
            "status": "analyzed",
            "quality": "good",
            "stats": {
                "avg_slippage_pct": 0.25,
                "avg_latency_ms": 120.0,
                "total_orders": 15,
            },
            "recommendations": {"notes": "Execution quality is within normal parameters"},
        }
    )
    monkeypatch.setattr(
        "app.infrastructure.repositories.common.deps.create_slippage_analysis_service",
        lambda _settings: slippage_service,
    )

    service = UnifiedAttributionService()
    report = service.build_report(
        strategy_name="live",
        period="7d",
        positions=[{"symbol": "600519", "name": "茅台", "value": 100000, "return_pct": -1.0}],
        symbol="600519",
        include_slippage=True,
    )
    assert report.slippage is not None
    assert report.slippage.quality == "good"
    assert report.slippage.order_count == 15
    assert report.slippage.contribution_pct < 0
