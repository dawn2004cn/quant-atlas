"""Regression tests for DecisionReviewQueue (Phase 5.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.system.services.ui.decision_review_queue import (
    DecisionReviewQueue,
    PendingDecision,
    ReviewCorrection,
    ReviewPriority,
    ReviewStatus,
)


@pytest.fixture
def review_queue(tmp_path: Path) -> DecisionReviewQueue:
    return DecisionReviewQueue(store_path=tmp_path / "queue.json", max_pending=200)


class TestDecisionReviewQueue:
    """Human-in-the-loop review queue."""

    def test_enqueue_creates_pending(self, review_queue):
        d = review_queue.enqueue("dec_001", "CN:600519", 0.45, "low_confidence")
        assert d.decision_id == "dec_001"
        assert d.status == ReviewStatus.PENDING
        assert d.confidence == 0.45

    def test_enqueue_duplicate_returns_same(self, review_queue):
        d1 = review_queue.enqueue("dec_001", "CN:600519", 0.45, "test")
        d2 = review_queue.enqueue("dec_001", "CN:600519", 0.45, "test")
        assert d1.decision_id == d2.decision_id

    def test_list_pending(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        review_queue.enqueue("dec_002", "B", 0.3, "test")
        pending = review_queue.list_pending()
        assert len(pending) == 2

    def test_approve(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        approved = review_queue.approve("dec_001")
        assert approved is not None
        assert approved.status == ReviewStatus.APPROVED

    def test_approve_nonexistent(self, review_queue):
        assert review_queue.approve("nonexistent") is None

    def test_reject(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        rejected = review_queue.reject("dec_001")
        assert rejected is not None
        assert rejected.status == ReviewStatus.REJECTED

    def test_add_correction(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        corr = review_queue.add_correction("dec_001", 1, "news", "ignore_evidence", comment="outdated")
        assert corr is not None
        assert corr.action == "ignore_evidence"
        assert corr.target_phase == "news"

        dec = review_queue.get_pending("dec_001")
        assert dec.status == ReviewStatus.CORRECTED

    def test_add_correction_nonexistent(self, review_queue):
        corr = review_queue.add_correction("nonexistent", 1, "x", "x")
        assert corr is None

    def test_get_pending(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        dec = review_queue.get_pending("dec_001")
        assert dec is not None
        assert dec.decision_id == "dec_001"

    def test_get_pending_nonexistent(self, review_queue):
        assert review_queue.get_pending("nonexistent") is None

    def test_get_pending_after_approve(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.4, "test")
        review_queue.approve("dec_001")
        dec = review_queue.get_pending("dec_001")
        assert dec.status == ReviewStatus.APPROVED

    def test_stats(self, review_queue):
        review_queue.enqueue("dec_001", "A", 0.3, "first")
        review_queue.enqueue("dec_002", "B", 0.4, "second")
        review_queue.approve("dec_001")
        stats = review_queue.stats()
        assert stats["total"] == 2
        assert stats["by_status"].get("pending", 0) == 1
        assert stats["by_status"].get("approved", 0) == 1

    def test_list_pending_limit(self, review_queue):
        for i in range(10):
            review_queue.enqueue(f"dec_{i:03d}", f"sub_{i}", 0.5, "test")
        assert len(review_queue.list_pending(limit=3)) <= 3

    def test_review_correction_dataclass(self):
        corr = ReviewCorrection(correction_id="c1", decision_id="d1", user_id=1, target_phase="analysis", action="adjust_confidence")
        assert corr.correction_id == "c1"
        assert corr.action == "adjust_confidence"

    def test_pending_decision_dataclass(self):
        dec = PendingDecision(decision_id="d1", subject="A", confidence=0.5, reason="test")
        assert dec.priority == ReviewPriority.NORMAL.value
        assert dec.corrections == []

    def test_persistence(self, tmp_path):
        q1 = DecisionReviewQueue(store_path=tmp_path / "q.json")
        q1.enqueue("persist_001", "A", 0.5, "test")
        q2 = DecisionReviewQueue(store_path=tmp_path / "q.json")
        assert len(q2.list_pending()) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
