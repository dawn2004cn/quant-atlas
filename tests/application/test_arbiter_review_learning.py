from __future__ import annotations

from pathlib import Path

from app.application.services.orchestration.arbiter_review_learning_service import (
    ArbiterReviewLearningService,
)


def test_review_adjusts_bullish_weight_after_wrong_call(tmp_path: Path) -> None:
    svc = ArbiterReviewLearningService(store_path=tmp_path / "learning.json")
    before = svc.get_stance_weights()["bullish"]
    svc.record_review(
        provenance_id="prov-1",
        symbol="600519",
        market="CN",
        predicted_verdict="bullish",
        actual_outcome="loss",
        pnl_pct=-3.2,
    )
    after = svc.get_stance_weights()["bullish"]
    assert after < before


def test_correct_review_does_not_adjust(tmp_path: Path) -> None:
    svc = ArbiterReviewLearningService(store_path=tmp_path / "learning.json")
    before = svc.get_stance_weights()
    svc.record_review(
        provenance_id="prov-2",
        symbol="600519",
        market="CN",
        predicted_verdict="bullish",
        actual_outcome="gain",
        pnl_pct=2.0,
    )
    assert svc.get_stance_weights()["bullish"] == before["bullish"]
