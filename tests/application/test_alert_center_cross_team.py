from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.modules.collaboration.services.cross_team_meta_learning_service import (
    CrossTeamMetaLearningService,
)
from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.core.event_bus import CrossTeamSiteAlertEvent, get_event_bus
from app.infrastructure.collaboration.cross_team_store import CrossTeamStore


def test_alert_center_includes_cross_team_consensus(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    cross = CrossTeamMetaLearningService(store=store, secret="t", min_teams=2)
    for tid in (1, 2):
        cross.register_team_consensus(
            team_id=tid,
            symbol="sz000002",
            market="CN",
            verdict="bearish",
            confidence=0.8,
        )
    svc = AlertCenterService(cross_team_service=cross)
    feed = svc.list_alerts(limit=50, include_system_probes=False)
    consensus = [i for i in feed.items if i.category == "consensus"]
    assert len(consensus) >= 1
    assert consensus[0].meta.get("verdict") == "bearish"


def test_site_alert_publishes_event(tmp_path: Path) -> None:
    bus = get_event_bus()
    bus.clear()
    received: list[CrossTeamSiteAlertEvent] = []

    def _capture(event: CrossTeamSiteAlertEvent) -> None:
        received.append(event)

    bus.subscribe(CrossTeamSiteAlertEvent, _capture)
    store = CrossTeamStore(base_dir=tmp_path)
    cross = CrossTeamMetaLearningService(store=store, secret="t", min_teams=2)
    for tid in (10, 11):
        cross.register_team_consensus(
            team_id=tid,
            symbol="sz600519",
            market="CN",
            verdict="bullish",
            confidence=0.7,
        )
    assert len(received) >= 1
    assert received[-1].symbol == "sz600519"
    assert received[-1].verdict == "bullish"
