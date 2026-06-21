"""Phase E — observability snapshot, billing placeholder, CI collection fix."""

from __future__ import annotations

from types import SimpleNamespace


def test_observability_snapshot_builds():
    from app.modules.system.services.system.observability_snapshot_service import (
        ObservabilitySnapshotService,
    )
    from app.presentation.api.v1_context import ApiV1Context

    ctx = ApiV1Context(
        market_service=object(),
        stock_service=object(),
        watchlist_service=object(),
        stock_group_service=object(),
        daily_workbench_service=object(),
        recommendation_service=object(),
        task_message_store=object(),
    )
    snap = ObservabilitySnapshotService().build_snapshot(ctx)
    assert snap["overall_status"] in ("ok", "degraded", "critical")
    assert snap["pulse"]["components"]
    assert snap["sla"]["uptime_target_pct"] == 99.0
    assert snap["critical_services"]["ok"] is True


def test_billing_status_beta():
    from app.domain.billing.retail_billing import build_billing_status

    status = build_billing_status(SimpleNamespace(role="free"))
    assert status["enabled"] is False
    assert status["provider"] == "stripe"
    assert status["tier"] == "free"


def test_billing_status_pro_tier():
    from app.domain.billing.retail_billing import build_billing_status

    status = build_billing_status(SimpleNamespace(role="pro"))
    assert status["tier"] == "pro"
    assert status["checkout_available"] is False
