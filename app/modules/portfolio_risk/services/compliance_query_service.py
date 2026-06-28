"""Compliance violation query service — list and search violation logs."""

from __future__ import annotations

from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


class ComplianceQueryService:
    """Read-only query layer over compliance_violations table."""

    def __init__(self, session=None):
        self._session = session

    def list_violations(
        self,
        *,
        user_id: int | None = None,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        """Paginated list of compliance violations."""
        session = self._session
        if session is None:
            return {"violations": [], "total": 0, "page": page, "per_page": per_page}

        from app.infrastructure.database.models import ComplianceViolationLog

        query = session.query(ComplianceViolationLog)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        if symbol is not None:
            query = query.filter_by(symbol=symbol.upper())
        if start is not None:
            query = query.filter(ComplianceViolationLog.created_at >= start)
        if end is not None:
            query = query.filter(ComplianceViolationLog.created_at <= end)

        total = query.count()
        violations = (
            query.order_by(ComplianceViolationLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "violations": [
                {
                    "id": v.id,
                    "order_id": v.order_id,
                    "user_id": v.user_id,
                    "symbol": v.symbol,
                    "violation_detail": v.violation_detail,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in violations
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def get_violation(self, violation_id: int) -> dict | None:
        """Get a single violation by ID."""
        session = self._session
        if session is None:
            return None

        from app.infrastructure.database.models import ComplianceViolationLog
        v = session.query(ComplianceViolationLog).filter_by(id=violation_id).first()
        if v is None:
            return None
        return {
            "id": v.id,
            "order_id": v.order_id,
            "user_id": v.user_id,
            "symbol": v.symbol,
            "violation_detail": v.violation_detail,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }

    def count_by_user(self, user_id: int, days: int = 7) -> int:
        """Count violations for a user in the last N days."""
        from datetime import timedelta

        from app.infrastructure.database.models import ComplianceViolationLog

        session = self._session
        if session is None:
            return 0

        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            session.query(ComplianceViolationLog)
            .filter(
                ComplianceViolationLog.user_id == user_id,
                ComplianceViolationLog.created_at >= cutoff,
            )
            .count()
        )
