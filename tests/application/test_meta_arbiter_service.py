from __future__ import annotations

from pathlib import Path

from app.modules.collaboration.services.cross_team_meta_learning_service import (
    CrossTeamMetaLearningService,
)
from app.application.services.orchestration.meta_arbiter_service import MetaArbiterService
from app.infrastructure.collaboration.cross_team_store import CrossTeamStore


def test_meta_arbiter_synthesizes_when_three_teams_agree(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    meta = MetaArbiterService(cross_team_store=store, min_teams=3)
    for team_id in (1, 2, 3):
        store.append_consensus(
            {
                "team_fp": f"tf-{team_id}",
                "symbol": "sz000001",
                "market": "CN",
                "verdict": "bullish",
                "confidence": 0.8,
                "created_at": "2099-01-01T00:00:00",
            }
        )
    out = meta.synthesize("sz000001", "CN", verdict_hint="bullish")
    assert out["ok"] is True
    assert out["meta_verdict"] == "bullish"
    assert out["team_count"] == 3
    assert out["meta_confidence"] > 0.5
    recent = meta.list_recent()
    assert recent["count"] >= 1


def test_site_alert_includes_meta_arbitration(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    meta = MetaArbiterService(cross_team_store=store, min_teams=3)
    svc = CrossTeamMetaLearningService(
        store=store,
        secret="test-secret",
        min_teams=3,
        meta_arbiter_service=meta,
    )
    for team_id in (10, 11, 12):
        svc.register_team_consensus(
            team_id=team_id,
            symbol="sz000338",
            market="CN",
            verdict="bearish",
            confidence=0.82,
        )
    alerts = svc.list_site_alerts()
    assert alerts["count"] >= 1
    row = alerts["alerts"][0]
    assert row.get("meta_verdict") == "bearish"
    assert row.get("meta_confidence", 0) > 0


def test_insufficient_teams_returns_error(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    meta = MetaArbiterService(cross_team_store=store, min_teams=3)
    store.append_consensus(
        {
            "team_fp": "tf-1",
            "symbol": "sz000002",
            "market": "CN",
            "verdict": "bullish",
            "confidence": 0.9,
            "created_at": "2099-01-01T00:00:00",
        }
    )
    out = meta.synthesize("sz000002", "CN")
    assert out["ok"] is False
    assert out["error"] == "insufficient_team_consensus"
