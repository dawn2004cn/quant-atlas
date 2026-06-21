from __future__ import annotations

from pathlib import Path

from app.modules.collaboration.services.cross_team_meta_learning_service import (
    CrossTeamMetaLearningService,
)
from app.infrastructure.collaboration.cross_team_store import CrossTeamStore


def test_site_alert_when_three_teams_agree(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    svc = CrossTeamMetaLearningService(store=store, secret="test-secret", min_teams=3)
    for team_id in (1, 2, 3):
        out = svc.register_team_consensus(
            team_id=team_id,
            symbol="sz000001",
            market="CN",
            verdict="bullish",
            confidence=0.75,
        )
        assert out["ok"] is True
    alerts = svc.list_site_alerts()
    assert alerts["count"] >= 1
    assert alerts["alerts"][0]["verdict"] == "bullish"
    assert alerts["alerts"][0]["team_count"] >= 3


def test_anonymous_pattern_no_symbol_in_pool(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    svc = CrossTeamMetaLearningService(store=store, secret="test-secret")
    svc.share_pattern_from_review(
        predicted_verdict="bullish",
        actual_outcome="loss",
        market="CN",
        pnl_pct=-2.5,
    )
    patterns = svc.list_anonymous_patterns()
    assert patterns["count"] == 1
    row = patterns["patterns"][0]
    assert "symbol" not in row
    assert row["failure_count"] == 1
    assert row["pattern_key"] == "bullish->loss"


def test_team_fingerprint_is_anonymized(tmp_path: Path) -> None:
    store = CrossTeamStore(base_dir=tmp_path)
    svc = CrossTeamMetaLearningService(store=store, secret="test-secret")
    fp = svc._team_fingerprint(42)
    assert fp.startswith("tf-")
    assert "42" not in fp
