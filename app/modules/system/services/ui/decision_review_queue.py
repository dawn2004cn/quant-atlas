"""Decision review queue — human-in-the-loop correction mechanism.

Phase 5.4 — holds decisions that need human review (low confidence,
high risk) and allows interactive correction of AI reasoning traces.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import BASE_DIR

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class ReviewPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


DEFAULT_REVIEW_SLA_HOURS = 24


@dataclass(frozen=True)
class ReviewCorrection:
    """A user correction applied to a decision's reasoning trace."""

    correction_id: str
    decision_id: str
    user_id: int
    target_phase: str
    action: str  # "ignore_evidence", "adjust_confidence", "add_context", "override_conclusion"
    payload: dict[str, Any] = field(default_factory=dict)
    comment: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class PendingDecision:
    """A decision awaiting human review."""

    decision_id: str
    subject: str
    confidence: float
    reason: str  # why it was flagged for review
    status: ReviewStatus = ReviewStatus.PENDING
    priority: str = ReviewPriority.NORMAL.value
    review_by: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    corrections: list[ReviewCorrection] = field(default_factory=list)


class DecisionReviewQueue:
    """In-memory + file-backed review queue for low-confidence decisions."""

    def __init__(self, *, store_path: Path | None = None, max_pending: int = 200) -> None:
        self._path = Path(store_path or BASE_DIR / "instance" / "decision_review_queue.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, PendingDecision] = {}
        self._lock = threading.Lock()
        self._max_pending = max_pending
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw:
                corrections = [
                    ReviewCorrection(**c) for c in item.get("corrections", [])
                ]
                dec = PendingDecision(
                    decision_id=item["decision_id"],
                    subject=item["subject"],
                    confidence=item["confidence"],
                    reason=item["reason"],
                    status=ReviewStatus(item.get("status", "pending")),
                    priority=str(item.get("priority", ReviewPriority.NORMAL.value)),
                    review_by=str(item.get("review_by", "")),
                    created_at=item.get("created_at", ""),
                    corrections=corrections,
                )
                self._pending[dec.decision_id] = dec
        except Exception as exc:
            logger.warning("DecisionReviewQueue load: %s", exc)

    def _persist(self) -> None:
        try:
            rows = []
            for dec in self._pending.values():
                rows.append({
                    "decision_id": dec.decision_id,
                    "subject": dec.subject,
                    "confidence": dec.confidence,
                    "reason": dec.reason,
                    "status": dec.status.value,
                    "priority": dec.priority,
                    "review_by": dec.review_by,
                    "created_at": dec.created_at,
                    "corrections": [
                        {
                            "correction_id": c.correction_id,
                            "decision_id": c.decision_id,
                            "user_id": c.user_id,
                            "target_phase": c.target_phase,
                            "action": c.action,
                            "payload": c.payload,
                            "comment": c.comment,
                            "created_at": c.created_at,
                        }
                        for c in dec.corrections
                    ],
                })
            self._path.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("DecisionReviewQueue persist: %s", exc)

    def enqueue(
        self,
        decision_id: str,
        subject: str,
        confidence: float,
        reason: str,
        *,
        priority: str = ReviewPriority.NORMAL.value,
        review_sla_hours: int = DEFAULT_REVIEW_SLA_HOURS,
    ) -> PendingDecision:
        """Add a decision to the review queue."""
        review_by = (
            datetime.now(timezone.utc) + timedelta(hours=max(1, review_sla_hours))
        ).isoformat().replace("+00:00", "Z")
        with self._lock:
            if decision_id in self._pending:
                return self._pending[decision_id]
            if len(self._pending) >= self._max_pending:
                oldest = next(iter(self._pending))
                del self._pending[oldest]
            dec = PendingDecision(
                decision_id=decision_id,
                subject=subject,
                confidence=confidence,
                reason=reason,
                priority=priority,
                review_by=review_by,
            )
            self._pending[decision_id] = dec
            self._persist()
        return dec

    def approve(self, decision_id: str) -> PendingDecision | None:
        with self._lock:
            dec = self._pending.get(decision_id)
            if dec is None:
                return None
            self._pending[decision_id] = PendingDecision(
                decision_id=dec.decision_id,
                subject=dec.subject,
                confidence=dec.confidence,
                reason=dec.reason,
                status=ReviewStatus.APPROVED,
                priority=dec.priority,
                review_by=dec.review_by,
                created_at=dec.created_at,
                corrections=dec.corrections,
            )
            self._persist()
            return self._pending[decision_id]

    def reject(self, decision_id: str) -> PendingDecision | None:
        with self._lock:
            dec = self._pending.get(decision_id)
            if dec is None:
                return None
            self._pending[decision_id] = PendingDecision(
                decision_id=dec.decision_id,
                subject=dec.subject,
                confidence=dec.confidence,
                reason=dec.reason,
                status=ReviewStatus.REJECTED,
                priority=dec.priority,
                review_by=dec.review_by,
                created_at=dec.created_at,
                corrections=dec.corrections,
            )
            self._persist()
            return self._pending[decision_id]

    def add_correction(
        self,
        decision_id: str,
        user_id: int,
        target_phase: str,
        action: str,
        payload: dict[str, Any] | None = None,
        comment: str = "",
    ) -> ReviewCorrection | None:
        """Apply a user correction to a pending decision."""
        import uuid

        with self._lock:
            dec = self._pending.get(decision_id)
            if dec is None:
                return None
            correction = ReviewCorrection(
                correction_id=f"corr_{uuid.uuid4().hex[:12]}",
                decision_id=decision_id,
                user_id=user_id,
                target_phase=target_phase,
                action=action,
                payload=payload or {},
                comment=comment,
            )
            updated = PendingDecision(
                decision_id=dec.decision_id,
                subject=dec.subject,
                confidence=dec.confidence,
                reason=dec.reason,
                status=ReviewStatus.CORRECTED,
                priority=dec.priority,
                review_by=dec.review_by,
                created_at=dec.created_at,
                corrections=[*dec.corrections, correction],
            )
            self._pending[decision_id] = updated
            self._persist()
        return correction

    def get_pending(self, decision_id: str) -> PendingDecision | None:
        with self._lock:
            return self._pending.get(decision_id)

    def list_recent(
        self,
        *,
        status: ReviewStatus | None = ReviewStatus.PENDING,
        limit: int = 50,
    ) -> list[PendingDecision]:
        with self._lock:
            items = list(self._pending.values())
        if status is not None:
            items = [d for d in items if d.status == status]
        items.sort(key=lambda d: d.created_at, reverse=True)
        return items[:limit]

    def list_pending(self, *, limit: int = 50) -> list[PendingDecision]:
        return self.list_recent(status=ReviewStatus.PENDING, limit=limit)

    def product_summary(self) -> dict[str, Any]:
        """Compact metrics for workbench / profile surfaces."""
        now = datetime.now(timezone.utc)
        pending = self.list_pending(limit=500)
        overdue = 0
        for dec in pending:
            if not dec.review_by:
                continue
            try:
                deadline = datetime.fromisoformat(dec.review_by.replace("Z", "+00:00"))
            except ValueError:
                continue
            if deadline < now:
                overdue += 1
        high_priority = sum(1 for d in pending if d.priority == ReviewPriority.HIGH.value)
        return {
            "pending_count": len(pending),
            "overdue_count": overdue,
            "high_priority_count": high_priority,
            "sla_hours": DEFAULT_REVIEW_SLA_HOURS,
            "cta": "请在复核截止前完成确认、驳回或修正",
            "oldest_pending_at": pending[-1].created_at if pending else None,
        }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status = {}
            for dec in self._pending.values():
                by_status[dec.status.value] = by_status.get(dec.status.value, 0) + 1
            return {"total": len(self._pending), "by_status": by_status}


_review_queue: DecisionReviewQueue | None = None
_review_lock = threading.Lock()


def get_review_queue() -> DecisionReviewQueue:
    global _review_queue
    if _review_queue is None:
        with _review_lock:
            if _review_queue is None:
                _review_queue = DecisionReviewQueue()
    return _review_queue


__all__ = [
    "DecisionReviewQueue",
    "PendingDecision",
    "ReviewCorrection",
    "ReviewPriority",
    "ReviewStatus",
    "DEFAULT_REVIEW_SLA_HOURS",
    "get_review_queue",
]
