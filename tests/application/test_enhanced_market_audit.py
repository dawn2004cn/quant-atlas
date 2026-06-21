"""Tests for Phase 9 Directive 3: recursive logic self-audit within market service."""
from __future__ import annotations

from app.modules.market_data.services.enhanced_market_service import EnhancedMarketService


class _FakeProvider:
    pass


def test_cross_validate_indicators_returns_drift_report():
    svc = EnhancedMarketService(sync_provider=_FakeProvider())
    report = svc.cross_validate_indicators("000001", [10.0, 11.0, 12.0, 13.0])
    assert report["ok"] is True
    assert "deviation_detected" in report
    assert "drifts" in report
    assert "drift_count" in report


def test_cross_validate_short_history_graceful():
    svc = EnhancedMarketService(sync_provider=_FakeProvider())
    report = svc.cross_validate_indicators("000001", [10.0])
    assert report["ok"] is True
    assert report["drift_count"] == 0
