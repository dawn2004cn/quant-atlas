from __future__ import annotations

from unittest.mock import MagicMock

from app.core.event_bus import AnalysisStaleEvent, EventBus, TruthDeviationEvent
from app.domain.verification import clear_pending, get_verification_status, list_pending
from app.infrastructure.realtime.truth_sentry import TruthSentry


def test_truth_sentry_publishes_on_anomaly() -> None:
    bus = EventBus()
    bus.clear()
    clear_pending("600519", "CN")

    mock_quality = MagicMock()
    mock_quality.compare_sources.return_value = [
        MagicMock(
            anomaly=True,
            field="close_price",
            source_a="TDX",
            source_b="Qlib",
            value_a=100.0,
            value_b=105.0,
            diff_pct=5.0,
        )
    ]

    received: list[str] = []
    bus.subscribe(TruthDeviationEvent, lambda _e: received.append("truth"))
    bus.subscribe(AnalysisStaleEvent, lambda _e: received.append("stale"))

    sentry = TruthSentry(mock_quality, diff_threshold_pct=0.5)
    sentry.check_symbol("600519", "CN")

    assert "truth" in received
    assert "stale" in received
    assert get_verification_status("600519", "CN") == "pending"
    assert "CN:600519" in list_pending()
